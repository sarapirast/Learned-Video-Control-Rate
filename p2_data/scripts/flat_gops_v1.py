"""GOPs whose score is not meaningful under the mean-of-frames YUV PSNR convention (tracker item 21c, 2026-11-09).

Rule (Aayush, 2026-11-09): exclude a GOP from score means when its constant-QP YUV PSNR at QP 50
(rd_native psnr_yuv_mean_frames) is above 45 dB on EITHER encoder, so both encoders drop the same GOPs.
Normal content tops out at 41.0 dB at QP 50; the next value is 45.1, so 45 sits in the gap.

Cause: these are grayscale (or partly grayscale) GOPs. Luma PSNR at QP 50 is a normal ~25 dB, but chroma is coded
without error (U/V MSE = 0 on 48 of the 58), so per-frame U/V PSNR hits its cap and dominates the YUV mean. Then a
plan with a little more luma distortion on a few frames gets a much lower mean PSNR, and "% bits saved at equal PSNR"
goes to -100s (down to -1e34 on train where the curve is extrapolated).

  python -I scripts/flat_gops_v1.py
Out: data/v1/320x180/rd/flat_gops.csv (clip_id, gop, start_frame, gid, split, label, psnr50_x264, psnr50_x265,
     chroma_mse0_x264, chroma_mse0_x265, flat)
"""
import pandas as pd

ROOT = "/scratch1/aayushso/ee599/data/v1/320x180"
THR = 45.0


def main():
    d = pd.read_parquet(f"{ROOT}/rd/rd_native.parquet").query("qp == 50")
    d = d.assign(mse0=(d.mse_u + d.mse_v) == 0)
    w = d.pivot_table(index=["clip_id", "gop"], columns="encoder", values=["psnr_yuv_mean_frames", "mse0"],
                      aggfunc="first")
    out = pd.DataFrame({"psnr50_x264": w[("psnr_yuv_mean_frames", "x264")],
                        "psnr50_x265": w[("psnr_yuv_mean_frames", "x265")],
                        "chroma_mse0_x264": w[("mse0", "x264")].astype(bool),
                        "chroma_mse0_x265": w[("mse0", "x265")].astype(bool)}).reset_index()
    g = pd.read_csv(f"{ROOT}/gops.csv")[["clip_id", "gop", "start_frame", "split", "label"]]
    out = g.merge(out, on=["clip_id", "gop"], how="left", validate="one_to_one")
    assert out.psnr50_x264.notna().all() and out.psnr50_x265.notna().all()
    out["gid"] = out.clip_id + "@" + out.start_frame.astype(str)
    out["flat"] = (out.psnr50_x264 > THR) | (out.psnr50_x265 > THR)
    cols = ["clip_id", "gop", "start_frame", "gid", "split", "label", "psnr50_x264", "psnr50_x265",
            "chroma_mse0_x264", "chroma_mse0_x265", "flat"]
    out[cols].to_csv(f"{ROOT}/rd/flat_gops.csv", index=False, float_format="%.3f")
    f = out[out.flat]
    print(f"{len(f)} of {len(out)} GOPs flagged (>{THR} dB at QP 50 on either encoder), {f.clip_id.nunique()} clips")
    print(f.groupby("split").size().to_string())
    print(f.groupby(["split", "clip_id"]).size().to_string())
    print(f"chroma MSE = 0 on both encoders: {(f.chroma_mse0_x264 & f.chroma_mse0_x265).sum()}")


if __name__ == "__main__":
    main()
