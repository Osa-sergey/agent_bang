import hashlib
import json
import os
import uuid

from omegaconf import OmegaConf
import mlflow

from src.game.Config import Config


class GameExperimentLogger:
    def __init__(self):
        self.__prepare_for_experiment()

    @staticmethod
    def start_run():
        run_name = os.path.basename(Config().config.save_path)
        mlflow.start_run(run_name=run_name)
        config = OmegaConf.to_container(Config().config, resolve=True)
        GameExperimentLogger.__set_run_tags(config)
        mlflow.log_dict(config, "config.json")

    @staticmethod
    def __set_run_tags(config: dict):
        tags = {"players_number": int(config["players_number"])}
        agent_types = []
        for agent in config["agents"].values():
            agent_types.append(agent["agent_type"])
        tags["agent_types"] = sorted(set(agent_types))
        tags["num_agent_types"] = len(set(agent_types))
        mlflow.set_tags(tags)

    @staticmethod
    def end_run():
        mlflow.log_artifacts(Config().config.save_path, "logs")
        mlflow.end_run()

    @staticmethod
    def __prepare_for_experiment():
        Config.set_git_commit_hash()
        GameExperimentLogger.__check_config_hash()
        exp_path = Config().config.save_path
        run_id = str(uuid.uuid4())
        Config().config.save_path = os.path.join(exp_path, run_id)
        run_path = Config().config.save_path
        os.makedirs(run_path)
        mlflow.set_experiment(Config().config.exp_name)


    @staticmethod
    def __get_config_hash(config: dict) -> str:
        json_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    @staticmethod
    def __check_config_hash():
        config = OmegaConf.to_container(Config().config, resolve=True)
        exp_save_path = config["save_path"]
        exp_hash = GameExperimentLogger.__get_config_hash(config)
        hash_file_path = os.path.join(exp_save_path, 'exp_hash.txt')
        if os.path.isdir(exp_save_path):
            with open(hash_file_path, 'r') as f:
                file_exp_hash = f.read()
            if exp_hash != file_exp_hash:
                raise Exception("Hash from experiment config must be the same for all runs!!!"
                                " Please change the exp_name or use correct config")
        else:
            os.makedirs(exp_save_path)
            with open(hash_file_path, 'w') as f:
                f.write(exp_hash)