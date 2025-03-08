from omegaconf import OmegaConf

class Config:
    _instance = None


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.config = None
        return cls._instance

    @classmethod
    def init(cls, path: str):
        if cls._instance.config is None:
            cls._instance.config = OmegaConf.load(path)
