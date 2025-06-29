import torch
import random
import numpy as np
from collections import deque
from game_level1 import Level1AI, Direction, Point
from model import Linear_QNet
from helper import plot
import sys
import os
from trainer import QTrainer


MAX_MEMORY = 100_000
BATCH_SIZE = 1000
LR = 0.001

class Agent:
    def __init__(self):
        self.n_games = 0
        self.epsilon = 0  # randomness
        self.gamma = 0.9  # discount rate
        self.memory = deque(maxlen=MAX_MEMORY)
        self.model = Linear_QNet(12, 256, 4)
        self.target_model = Linear_QNet(12, 256, 4)
        self.trainer = QTrainer(self.model, lr=LR, gamma=self.gamma)
        self.update_target()

    def update_target(self):
        self.target_model.load_state_dict(self.model.state_dict())

    def get_state(self, game):
        head = game.snake[0]
        point_l = Point(head.x - 20, head.y)
        point_r = Point(head.x + 20, head.y)
        point_u = Point(head.x, head.y - 20)
        point_d = Point(head.x, head.y + 20)

        dir_l = game.direction == Direction.LEFT
        dir_r = game.direction == Direction.RIGHT
        dir_u = game.direction == Direction.UP
        dir_d = game.direction == Direction.DOWN

        state = [
            (dir_r and game.is_collision(point_r)),
            (dir_l and game.is_collision(point_l)),
            (dir_u and game.is_collision(point_u)),
            (dir_d and game.is_collision(point_d)),

            dir_l,
            dir_r,
            dir_u,
            dir_d,

            game.food.x < game.head.x,
            game.food.x > game.head.x,
            game.food.y < game.head.y,
            game.food.y > game.head.y
        ]

        return np.array(state, dtype=int)

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def train_long_memory(self):
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE)
        else:
            mini_sample = self.memory

        states, actions, rewards, next_states, dones = zip(*mini_sample)
        self.trainer.train_step(states, actions, rewards, next_states, dones, self.target_model)

    def train_short_memory(self, state, action, reward, next_state, done):
        self.trainer.train_step([state], [action], [reward], [next_state], [done], self.target_model)

    def get_action(self, state):
        self.epsilon = max(10, 80 - self.n_games)
        final_move = [0, 0, 0, 0]
        if random.randint(0, 200) < self.epsilon:
            move = random.randint(0, 3)
            final_move[move] = 1
        else:
            state0 = torch.tensor(state, dtype=torch.float)
            prediction = self.model(state0)
            move = torch.argmax(prediction).item()
            final_move[move] = 1
        return final_move

def train(game):
    plot_scores = []
    plot_mean_scores = []
    total_score = 0
    record = 0
    agent = Agent()

    while True:
        state_old = agent.get_state(game)
        final_move = agent.get_action(state_old)
        reward, done, score = game.play_step(final_move)
        state_new = agent.get_state(game)

        agent.train_short_memory(state_old, final_move, reward, state_new, done)
        agent.remember(state_old, final_move, reward, state_new, done)

        if done:
            game.reset()
            agent.n_games += 1
            agent.epsilon = max(0.01, agent.epsilon * 0.995)
            agent.train_long_memory()

            if agent.n_games % 10 == 0:
                agent.update_target()

            if score > record:
                record = score
                agent.model.save()
            plot_scores.append(score)
            total_score += score
            mean_score = total_score / agent.n_games
            plot_mean_scores.append(mean_score)
            plot(plot_scores, plot_mean_scores)

            # Stop after enough games
            if agent.n_games >= 500000:
                break

    print("Training finished.")
    from mainscreen import main_screen
    main_screen()
    sys.exit()

if __name__ == '__main__':
    train()
