from omegaconf import OmegaConf
from git import Repo

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


    @classmethod
    def set_git_commit_hash(cls):

        def __get_git_commit_hash():
            try:
                repo = Repo('.')
                commit_hash = repo.head.commit.hexsha[:8]
                return commit_hash
            except Exception as e:
                print(f"Error: Could not retrieve commit hash. {e}")
                return None

        cls._instance.config.git_hash = __get_git_commit_hash()