/*
 * encoder_shim.c — thin C layer over libx264 for the EE599 RL rate-control env.
 *
 * Python talks to this through ctypes using only plain ints and byte buffers,
 * so it never needs to know the layout of x264_param_t / x264_picture_t.
 *
 * Frozen encoder settings: see FROZEN_OPTS below and ENCODER_SETTINGS.md.
 * CQP with the QP of every frame forced through pic.i_qpplus1.
 *
 * Frames are passed as contiguous I420: Y (w*h), then U, V (w/2*h/2 each).
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <x264.h>

typedef struct {
    x264_t         *enc;
    x264_param_t    param;
    x264_picture_t  pic_in;   /* allocated with x264_picture_alloc */
    int             width, height;
    int             qp_min, qp_max;   /* range x264 actually honours */
    int64_t         next_pts;
} shim_t;

/* Settings fixed for the whole project (keep in sync with ENCODER_SETTINGS.md).
 * Order matters: preset medium is applied first, then these overrides. */
static const char *FROZEN_OPTS[][2] = {
    { "bframes",    "0"  },
    { "keyint",     "30" },
    { "min-keyint", "30" },
    { "scenecut",   "0"  },
    { "aq-mode",    "0"  },
    { "mbtree",     "0"  },
    { "psy",        "0"  },
    { "threads",    "1"  },
    /* "qp" switches rate control to CQP. Every frame gets a forced QP, so its
     * value matters only through the clamp: in CQP x264 overrides qpmin/qpmax
     * with [qp - 6*log2(ipratio), qp + 6*log2(pbratio)]. ipratio/pbratio are
     * capped at 10 (+-19.9 QP), so qp=31 gives the widest useful window,
     * [11, 51]. With bframes=0 and all QPs forced, the ratios affect nothing
     * else. */
    { "qp",         "31" },
    { "ipratio",    "10" },
    { "pbratio",    "10" },
    /* With the default variable-frame-rate input mode x264 holds each frame
     * until the next one arrives (to learn its duration), so encode() would
     * return frame t-1. force-cfr removes that 1-frame delay; only the SPS VUI
     * fixed_frame_rate flag changes. */
    { "force-cfr",  "1"  },
};

int shim_api_version(void) { return X264_BUILD; }

/* Returns an opaque handle, or NULL on failure (reason printed to stderr).
 * sar_w:sar_h is the sample aspect ratio written to the SPS VUI (0:0 = not
 * written); pass the y4m "A" value so the stream matches the x264 CLI. */
shim_t *shim_open(int width, int height, int fps_num, int fps_den,
                  int sar_w, int sar_h, int log_level)
{
    if (width <= 0 || height <= 0 || (width & 1) || (height & 1)) {
        fprintf(stderr, "shim_open: width/height must be positive and even\n");
        return NULL;
    }
    shim_t *s = calloc(1, sizeof(*s));
    if (!s) return NULL;

    if (x264_param_default_preset(&s->param, "medium", NULL) < 0) {
        fprintf(stderr, "shim_open: preset medium rejected\n");
        free(s);
        return NULL;
    }
    for (size_t i = 0; i < sizeof(FROZEN_OPTS) / sizeof(FROZEN_OPTS[0]); i++) {
        int rc = x264_param_parse(&s->param, FROZEN_OPTS[i][0], FROZEN_OPTS[i][1]);
        if (rc != 0) {
            fprintf(stderr, "shim_open: x264_param_parse(%s=%s) failed (%d)\n",
                    FROZEN_OPTS[i][0], FROZEN_OPTS[i][1], rc);
            x264_param_cleanup(&s->param);
            free(s);
            return NULL;
        }
    }

    /* Geometry / format: set directly. This is C compiled against the same
     * header, so the struct layout is not a concern here. */
    s->param.i_width     = width;
    s->param.i_height    = height;
    s->param.i_csp       = X264_CSP_I420;
    s->param.i_bitdepth  = 8;
    s->param.i_fps_num   = fps_num > 0 ? fps_num : 30;
    s->param.i_fps_den   = fps_den > 0 ? fps_den : 1;
    s->param.i_timebase_num = s->param.i_fps_den;
    s->param.i_timebase_den = s->param.i_fps_num;
    if (sar_w > 0 && sar_h > 0) {
        s->param.vui.i_sar_width  = sar_w;
        s->param.vui.i_sar_height = sar_h;
    }
    s->param.i_log_level = log_level;

    s->enc = x264_encoder_open(&s->param);
    if (!s->enc) {
        fprintf(stderr, "shim_open: x264_encoder_open failed\n");
        x264_param_cleanup(&s->param);
        free(s);
        return NULL;
    }
    if (x264_picture_alloc(&s->pic_in, X264_CSP_I420, width, height) < 0) {
        fprintf(stderr, "shim_open: x264_picture_alloc failed\n");
        x264_encoder_close(s->enc);
        x264_param_cleanup(&s->param);
        free(s);
        return NULL;
    }
    s->width  = width;
    s->height = height;
    /* Read back the effective parameters: in CQP mode x264 replaces
     * qpmin/qpmax inside its own copy, not in s->param. */
    x264_param_t eff;
    x264_encoder_parameters(s->enc, &eff);
    s->qp_min = eff.rc.i_qp_min;
    s->qp_max = eff.rc.i_qp_max;
    return s;
}

int shim_frame_size(const shim_t *s) { return s->width * s->height * 3 / 2; }

int shim_delayed_frames(shim_t *s) { return x264_encoder_delayed_frames(s->enc); }

/* QP range x264 will actually honour (forced QPs outside it are silently
 * clamped by x264; shim_encode rejects them instead). See FROZEN_OPTS. */
void shim_qp_range(const shim_t *s, int *qp_min, int *qp_max)
{
    if (qp_min) *qp_min = s->qp_min;
    if (qp_max) *qp_max = s->qp_max;
}

/* Copy x264's reconstructed picture into contiguous I420.
 * pic_out.img points at x264's internal recon, which is NV12 (Y plane +
 * interleaved UV plane) for 8-bit 4:2:0, not the I420 we fed in. Handle
 * NV12, I420 and YV12; return -4 for anything else. */
static int copy_recon(const shim_t *s, const x264_picture_t *pic, uint8_t *dst)
{
    const int W = s->width, H = s->height, cw = W / 2, ch = H / 2;
    const x264_image_t *img = &pic->img;
    const int csp = img->i_csp & X264_CSP_MASK;

    if (img->i_csp & X264_CSP_HIGH_DEPTH) return -4;
    for (int y = 0; y < H; y++, dst += W)
        memcpy(dst, img->plane[0] + (size_t)y * img->i_stride[0], W);

    if (csp == X264_CSP_NV12) {
        uint8_t *u = dst, *v = dst + (size_t)cw * ch;
        for (int y = 0; y < ch; y++) {
            const uint8_t *uv = img->plane[1] + (size_t)y * img->i_stride[1];
            for (int x = 0; x < cw; x++) {
                *u++ = uv[2 * x];
                *v++ = uv[2 * x + 1];
            }
        }
        return 0;
    }
    if (csp == X264_CSP_I420 || csp == X264_CSP_YV12) {
        const int pu = csp == X264_CSP_I420 ? 1 : 2, pv = 3 - pu;
        for (int y = 0; y < ch; y++, dst += cw)
            memcpy(dst, img->plane[pu] + (size_t)y * img->i_stride[pu], cw);
        for (int y = 0; y < ch; y++, dst += cw)
            memcpy(dst, img->plane[pv] + (size_t)y * img->i_stride[pv], cw);
        return 0;
    }
    return -4;
}

/* Shared tail of encode/flush: collect NALs, recon and frame info.
 * Returns 1 if a frame came out, 0 if none, negative on error. */
static int collect(shim_t *s, int frame_bytes, x264_nal_t *nals, int n_nal,
                   x264_picture_t *pic_out, uint8_t *bs_out, int bs_cap,
                   int *out_bytes, int *out_slice_bytes, uint8_t *recon_out,
                   int *out_type, long long *out_pts)
{
    if (frame_bytes < 0) return -1;
    if (frame_bytes == 0) return 0;
    if (bs_out && frame_bytes > bs_cap) return -2;

    /* Split the frame's NALs into slice (coded picture) bytes and header
     * bytes (SPS, PPS, SEI, AUD...). Sizes include the Annex-B start codes. */
    int off = 0, slice = 0;
    for (int i = 0; i < n_nal; i++) {
        if (bs_out) memcpy(bs_out + off, nals[i].p_payload, nals[i].i_payload);
        off += nals[i].i_payload;
        if (nals[i].i_type >= NAL_SLICE && nals[i].i_type <= NAL_SLICE_IDR)
            slice += nals[i].i_payload;
    }
    if (off != frame_bytes) return -5;   /* should never happen */

    if (out_bytes)       *out_bytes       = frame_bytes;
    if (out_slice_bytes) *out_slice_bytes = slice;
    if (recon_out && copy_recon(s, pic_out, recon_out) < 0) return -4;
    if (out_type)  *out_type  = pic_out->i_type;
    if (out_pts)   *out_pts   = pic_out->i_pts;
    return 1;
}

/*
 * Encode one input frame (contiguous I420, shim_frame_size() bytes) at `qp`.
 * Outputs (any may be NULL): Annex-B bitstream for the frame that came out,
 * its total size in bytes, the part of that which is slice NALs (the rest is
 * SPS/PPS/SEI headers), its reconstruction (contiguous I420), its type
 * (X264_TYPE_*), and its pts (input frame index).
 * Returns 1 if a frame was output, 0 if the encoder buffered it, <0 on error
 * (-3: qp outside the range x264 honours, see shim_qp_range).
 */
int shim_encode(shim_t *s, const uint8_t *yuv, int qp,
                uint8_t *bs_out, int bs_cap, int *out_bytes, int *out_slice_bytes,
                uint8_t *recon_out, int *out_type, long long *out_pts)
{
    if (qp < s->qp_min || qp > s->qp_max) return -3;
    const int w[3] = { s->width, s->width / 2, s->width / 2 };
    const int h[3] = { s->height, s->height / 2, s->height / 2 };
    const uint8_t *src = yuv;
    for (int p = 0; p < 3; p++) {
        for (int y = 0; y < h[p]; y++) {
            memcpy(s->pic_in.img.plane[p] + (size_t)y * s->pic_in.img.i_stride[p], src, w[p]);
            src += w[p];
        }
    }
    s->pic_in.i_pts     = s->next_pts++;
    s->pic_in.i_type    = X264_TYPE_AUTO;   /* keyint=30 decides I vs P */
    s->pic_in.i_qpplus1 = qp + 1;

    x264_nal_t *nals = NULL;
    int n_nal = 0;
    x264_picture_t pic_out;
    int bytes = x264_encoder_encode(s->enc, &nals, &n_nal, &s->pic_in, &pic_out);
    return collect(s, bytes, nals, n_nal, &pic_out, bs_out, bs_cap,
                   out_bytes, out_slice_bytes, recon_out, out_type, out_pts);
}

/* Drain one buffered frame. Same outputs/returns as shim_encode. */
int shim_flush(shim_t *s, uint8_t *bs_out, int bs_cap, int *out_bytes,
               int *out_slice_bytes, uint8_t *recon_out, int *out_type,
               long long *out_pts)
{
    if (x264_encoder_delayed_frames(s->enc) <= 0) return 0;
    x264_nal_t *nals = NULL;
    int n_nal = 0;
    x264_picture_t pic_out;
    int bytes = x264_encoder_encode(s->enc, &nals, &n_nal, NULL, &pic_out);
    return collect(s, bytes, nals, n_nal, &pic_out, bs_out, bs_cap,
                   out_bytes, out_slice_bytes, recon_out, out_type, out_pts);
}

void shim_close(shim_t *s)
{
    if (!s) return;
    x264_picture_clean(&s->pic_in);
    if (s->enc) x264_encoder_close(s->enc);
    x264_param_cleanup(&s->param);
    free(s);
}
