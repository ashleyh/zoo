import subprocess
import os

def make_guesser():
    from zoo.guesslang.trainer import Trainer
    from zoo import config
    import cPickle as pickle

    trainer = Trainer()
    trainer.train_on_dir(config.ZOO_GUESSLANG_TRAIN_DIR)
    guesser = trainer.make_guesser()

    with open(config.ZOO_GUESSLANG_PICKLE_PATH, 'w') as f:
        pickle.dump(guesser, f)

def main():
    make_guesser()

if __name__ == "__main__":
    main()

