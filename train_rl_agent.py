"""Train a Deep RL agent for BVR combat using PPO.

Uses Stable Baselines 3 and the custom BvrCombatEnv.
"""

import os
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnRewardThreshold

from simulation.rl_env import BvrCombatEnv


def main():
    # Model saving directory
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    model_path = models_dir / "ppo_bvr_agent"

    print("Initializing RL Environment...")
    env = BvrCombatEnv(scenario_path="data/scenario_configs/4v4_equal.yaml", dt=0.5)

    # Optional: use vectorized environments for faster training
    # vec_env = make_vec_env(lambda: env, n_envs=4)

    # 1. Initialize PPO
    # MlpPolicy is a standard fully connected neural network
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        tensorboard_log="./logs/ppo_bvr_tensorboard/"
    )

    # Callback to stop early if it gets really good (avoids training for hours for the demo)
    callback_on_best = StopTrainingOnRewardThreshold(reward_threshold=200, verbose=1)
    eval_callback = EvalCallback(
        env,
        callback_on_new_best=callback_on_best,
        eval_freq=5000,
        best_model_save_path=str(models_dir),
        verbose=1,
    )

    # 2. Train the Model
    # For a real project this should be 1,000,000+
    # For demonstration purposes, we run 10,000 steps.
    TOTAL_TIMESTEPS = 10000
    
    print(f"Starting PPO training for {TOTAL_TIMESTEPS} timesteps...")
    model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=eval_callback)

    # 3. Save the final model
    model.save(str(model_path))
    print(f"Training complete. Model saved to {model_path}.zip")


if __name__ == "__main__":
    main()
