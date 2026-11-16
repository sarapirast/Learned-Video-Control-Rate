from .encoder import Encoder, EncodedFrame, read_y4m, y4m_header, psnr_i420

__all__ = ["Encoder", "EncodedFrame", "read_y4m", "y4m_header", "psnr_i420", "RateControlEnv"]


def __getattr__(name):
    # Import the env lazily so the encoder still works without gymnasium/numpy.
    if name == "RateControlEnv":
        from .env import RateControlEnv
        return RateControlEnv
    raise AttributeError(name)
