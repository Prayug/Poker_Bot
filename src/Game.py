# possible additional ideas
# GUI stuff
# Multiplayer
# AI players
import eel
from itertools import combinations
import sys
import os
from typing import List, Tuple
from Deck import Deck  
from Card import Card, Suit, Value 
from AI_levels.AILevel1 import AIPlayerLevel1
from AI_levels.AILevel2 import AIPlayerLevel2
import sqlite3
from multiprocessing import Pool, cpu_count
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Player import Player

class PokerGame:
    def __init__(self, players, big):
        self.deck = Deck()
        self.players = players
        self.community_cards = []
        self.pot = 0
        self.highest_bet = 0
        self.flop_dealt = False
        self.turn_dealt = False
        self.river_dealt = False
        self.winner_paid = False
        self.is_showdown = False 
        self.current_dealer = 1  
        self.small_blind = 50
        self.big_blind = big
        self.log = []
        self.all_in_announcement = ""
        self.reset_game()
        self.ai_player = next((p for p in players if isinstance(p, AIPlayerLevel2)), None)
        self.create_hands_table()
        self.counter = 0
        self.player1Response = ""

    def create_hands_table(self):
        with sqlite3.connect('poker_odds.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Preflop (
                    card1 TEXT,
                    card2 TEXT,
                    win_rate REAL,
                    high_card REAL,
                    one_pair REAL,
                    two_pair REAL,
                    three_of_a_kind REAL,
                    straight REAL,
                    flush REAL,
                    full_house REAL,
                    four_of_a_kind REAL,
                    straight_flush REAL,
                    royal_flush REAL
                )
            ''')
            conn.commit()

    def deal_specific_cards(self, card1, card2):
        self.players[0].hand = [card1, card2]
        self.deck.remove(card1)
        self.deck.remove(card2)
        self.players[1].hand = [self.deck.deal(), self.deck.deal()]

    def deal_remaining_cards(self):
        self.deal_community_cards(3)
        self.deal_community_cards(1)
        self.deal_community_cards(1)


    def simulate_game_postFlop(self, bot_hand, flop_cards):
        bot_wins = 0
        newGame = PokerGame([Player("Alice", 10000), Player("Bob", 10000)], big = 100)  # Temporary game instance for simulation

        for _ in range(1000):
            newGame.reset_game()

            newGame.players[0].hand = [bot_hand[0], bot_hand[1]]
            newGame.deck.remove(bot_hand[0])
            newGame.deck.remove(bot_hand[1])


            newGame.community_cards.append(flop_cards[0])
            newGame.deck.remove(flop_cards[0])
            newGame.community_cards.append(flop_cards[1])
            newGame.deck.remove(flop_cards[1])
            newGame.community_cards.append(flop_cards[2])
            newGame.deck.remove(flop_cards[2])

            newGame.players[1].hand = [newGame.deck.deal(), newGame.deck.deal()]  
        
            newGame.deal_community_cards(1)
            newGame.deal_community_cards(1)

            if newGame.showdown() == newGame.players[0]:
                bot_wins += 1

        return (bot_wins / 1000) * 100

    def simulate_game_postTurn(self, bot_hand, comm_cards):
        bot_wins = 0
        newGame = PokerGame([Player("Alice", 10000), Player("Bob", 10000)], big = 100)  # Temporary game instance for simulation

        for _ in range(1000):
            newGame.reset_game()
            newGame.players[0].hand = [bot_hand[0], bot_hand[1]]
            newGame.deck.remove(bot_hand[0])
            newGame.deck.remove(bot_hand[1])
            newGame.community_cards.append(comm_cards[0])
            newGame.deck.remove(comm_cards[0])
            newGame.community_cards.append(comm_cards[1])
            newGame.deck.remove(comm_cards[1])
            newGame.community_cards.append(comm_cards[2])
            newGame.deck.remove(comm_cards[2])
            newGame.community_cards.append(comm_cards[3])
            newGame.deck.remove(comm_cards[3])
            newGame.players[1].hand = [newGame.deck.deal(), newGame.deck.deal()]  
            newGame.deal_community_cards(1)

            if newGame.showdown() == newGame.players[0]:
                bot_wins += 1

        return (bot_wins / 1000) * 100

    def make_decision_flop(self, bot_hand, flop_cards, player1Resp):        
        hand_strength = self.simulate_game_postFlop(bot_hand, flop_cards)

        print(hand_strength)

        # Decision threshold based on win rate
        call_threshold = 50  # Example threshold, can be adjusted

        if player1Resp == "Raise":
            if hand_strength >= call_threshold + 5:
                return "Call"
        if player1Resp == "Check":
            return "Call"
        return "Fold"  # AI folds if the hand strength is below the threshold
    
    def make_decision_turn(self, bot_hand, comm_cards):        
        hand_strength = self.simulate_game_postTurn(bot_hand, comm_cards)

        print(hand_strength)

        # Decision threshold based on win rate
        call_threshold = 50  # Example threshold, can be adjusted

        if hand_strength >= call_threshold:
            return "Call"
        return "Fold"  # AI folds if the hand strength is below the threshold
    

    def fold(self):
        if self.winner_paid == False:
            self.log.append(f"{self.players[0].name} folds.")
            self.players[1].chips += self.pot
            self.pot = 0
            self.log.append(f"{self.players[1].name} wins the pot.")
            self.reset_game()
            self.winner_paid = True
        
    def get_game_state(self):
        def get_card_image_path(card):
            rank = card.rank.value
            suit = card.suit.value
            return f"cards/{rank}{suit}.png"
        
        player1_best_hand, player1_hand_type = self.get_best_hand(self.players[0])

        return {
            "player1": {
                "name": self.players[0].name,
                "chips": self.players[0].chips,
                "hand": [get_card_image_path(card) for card in self.players[0].hand],
                "best_hand": player1_hand_type,
                "isFold": self.players[0].fold
            },
            "player2": {
                "name": self.players[1].name,
                "chips": self.players[1].chips,
                "hand": [get_card_image_path(card) for card in self.players[1].hand] if self.is_showdown or self.players[1].fold else ["cards/back.png" for card in self.players[1].hand],
                "isFold": self.players[1].fold
            },
            "community_cards": [get_card_image_path(card) for card in self.community_cards],
            "pot": self.pot,
            "highest_bet": self.highest_bet,
            "log": ["Game state updated"],
            "is_showdown": self.is_showdown,  
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "current_dealer": self.current_dealer
        }


    def get_best_hand(self, player):
        cards = player.hand + self.community_cards
        best_hand, hand_type = self.evaluate_hand(cards)
        return best_hand, hand_type
    

    def advance_game_stage(self):
        if not self.flop_dealt:
            self.deal_community_cards(3)
            self.flop_dealt = True
        elif not self.turn_dealt:
            self.deal_community_cards(1)
            self.turn_dealt = True
        elif not self.river_dealt:
            self.deal_community_cards(1)
            self.river_dealt = True
        else:
            if self.winner_paid == False:
                self.showdown()

    def reset_game(self):
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.highest_bet = 0
        self.flop_dealt = False
        self.turn_dealt = False
        self.river_dealt = False
        self.winner_paid = False
        self.is_showdown = False
        self.player_hand = ""
        for player in self.players:
            player.reset_hand()
        self.log = []

    def collect_blinds(self):
        if self.current_dealer == 0:  # Player1 is the dealer
            self.players[1].chips -= self.small_blind
            self.players[0].chips -= self.big_blind
            self.players[1].current_bet = self.small_blind
            self.players[0].current_bet = self.big_blind
        else:  # Player2 (AI) is the dealer
            self.players[0].chips -= self.small_blind
            self.players[1].chips -= self.big_blind
            self.players[0].current_bet = self.small_blind
            self.players[1].current_bet = self.big_blind
        self.pot += self.big_blind + self.small_blind
        self.highest_bet = self.big_blind

    def deal_cards(self):
        self.current_dealer = (self.current_dealer + 1) % 2 
        for player in self.players:
            player.setCards(self.deck.deal())
        for player in self.players:
            player.setCards(self.deck.deal())
        print(self.players[1].hand)


    def deal_community_cards(self, number):
        if number == 3 and not self.flop_dealt:
            self.community_cards.extend(self.deck.deal() for _ in range(3))
            self.flop_dealt = True
        elif number == 1 and not self.turn_dealt and self.flop_dealt:
            self.community_cards.append(self.deck.deal())
            self.turn_dealt = True
        elif number == 1 and not self.river_dealt and self.turn_dealt:
            self.community_cards.append(self.deck.deal())
            self.river_dealt = True

    def collect_bets(self, player_action, raise_amount=None):        
        if player_action == "check":
            if not self.flop_dealt and self.players[0].current_bet == self.small_blind:
                self.players[0].chips -= (self.big_blind - self.small_blind)
                self.pot += (self.big_blind - self.small_blind)
                self.players[0].current_bet = self.big_blind
            
            if not self.flop_dealt and self.players[1].current_bet == self.small_blind:
                self.players[1].chips -= (self.big_blind - self.small_blind)
                self.pot += (self.big_blind - self.small_blind)
                self.players[1].current_bet = self.big_blind

            if self.river_dealt:
                print("here")
            elif self.turn_dealt:
                print("monk")
            elif self.flop_dealt:
                print("ey")

            self.advance_game_stage()

        elif player_action == "raise" and raise_amount is not None:
            
            raise_amount = int(raise_amount)
            
            if not self.flop_dealt and self.players[0].current_bet == self.small_blind:
                self.players[0].chips -= (self.big_blind - self.small_blind)
                self.pot += (self.big_blind - self.small_blind)
                self.players[0].current_bet = self.big_blind
            
            if not self.flop_dealt and self.players[1].current_bet == self.small_blind:
                self.players[1].chips -= (self.big_blind - self.small_blind)
                self.pot += (self.big_blind - self.small_blind)
                self.players[1].current_bet = self.big_blind

            self.player_raise(self.players[0], raise_amount)
            
            if self.players[1].make_decision_pre() == "Call":
                self.ai_call(self.players[1], player_action)
            elif self.players[1].make_decision_pre() == "Raise":
                self.player_raise(self.players[1], 3 * self.big_blind)
            else:
                self.players[1].fold_hand()
                self.players[0].chips += self.pot
                self.pot = 0
                self.log.append(f"{self.players[0].name} wins the pot.")
                self.winner_paid = True
            
        return self.get_game_state()

    def play_round(self):
        self.reset_game()
        self.deal_cards()
    
    def showdown(self):
        self.is_showdown = True 

        player1_best_hand, player1_hand_type = self.evaluate_hand(self.players[0].hand + self.community_cards)
        player2_best_hand, player2_hand_type = self.evaluate_hand(self.players[1].hand + self.community_cards)
        
        if player1_best_hand > player2_best_hand:
            self.players[0].chips += self.pot
            self.player_hand = player1_hand_type
            self.winner_paid = True
            return self.players[0]
        elif player2_best_hand > player1_best_hand:
            self.players[1].chips += self.pot
            self.winner_paid = True
            return self.players[1]
        else:
            split_pot = self.pot // 2
            self.players[0].chips += split_pot
            self.players[1].chips += split_pot
            self.winner_paid = True
            return 0

    def evaluate_hand(self, cards: List[Card]) -> Tuple[Tuple[int, List[int]], str]:
        best_rank = (-1, [])
        best_hand_type = "High Card"
        
        for combo in combinations(cards, 5):
            rank, hand_type = self.rank_hand(combo)
            if rank > best_rank:
                best_rank = rank
                best_hand_type = hand_type
        return best_rank, best_hand_type

    def rank_hand(self, hand: List[Card]) -> Tuple[Tuple[int, List[int]], str]:
        
        values = sorted([card.rank.value for card in hand], reverse=True)
        suits = [card.suit for card in hand]
        
        is_flush = len(set(suits)) == 1
        is_straight = all(values[i] - values[i+1] == 1 for i in range(len(values) - 1))
        value_counts = {v: values.count(v) for v in values}
        counts = sorted(value_counts.values(), reverse=True)
        ranks_by_count = sorted(value_counts, key=lambda k: (value_counts[k], k), reverse=True)

        if is_straight and is_flush and values[0] == Value.ACE.value:
            return (10, values), "Royal Flush"
        if is_straight and is_flush:
            return (9, values), "Straight Flush"
        if counts == [4, 1]:
            return (8, ranks_by_count), "Four of a Kind"
        if counts == [3, 2]:
            return (7, ranks_by_count), "Full House"
        if is_flush:
            return (6, values), "Flush"
        if is_straight:
            return (5, values), "Straight"
        if counts == [3, 1, 1]:
            return (4, ranks_by_count), "Three of a Kind"
        if counts == [2, 2, 1]:
            return (3, ranks_by_count), "Two Pair"
        if counts == [2, 1, 1, 1]:
            return (2, ranks_by_count), "One Pair"
        return (1, values), "High Card"
    
    def player_raise(self, player, raise_amount):
        raise_amount = player.raise_bet(raise_amount)
        self.pot += raise_amount
        self.highest_bet = player.current_bet
        return raise_amount


    def ai_call(self, ai_player, player_action):
        if isinstance(ai_player, AIPlayerLevel1):
            call_amount = min(self.highest_bet, ai_player.chips)
            ai_player.current_bet = call_amount
            ai_player.chips -= call_amount
            self.pot += call_amount
            return call_amount
        elif isinstance(ai_player, AIPlayerLevel2):            
            if self.turn_dealt:
                if self.make_decision_turn(self.players[1].hand, self.community_cards) == "Call":
                    call_amount = min(self.highest_bet, ai_player.chips)
                    ai_player.current_bet = call_amount
                    ai_player.chips -= call_amount
                    self.pot += call_amount
                    return call_amount
                else:
                    self.players[1].fold_hand()
            elif self.flop_dealt:
                if self.make_decision_flop(self.players[1].hand, self.community_cards, player_action) == "Call":
                    call_amount = min(self.highest_bet, ai_player.chips)
                    ai_player.current_bet = call_amount
                    ai_player.chips -= call_amount
                    self.pot += call_amount
                    return call_amount
                else:
                    self.players[1].fold_hand()
            else:
                if ai_player.make_decision_pre() == "Raise":
                    self.player_raise(ai_player, 3 * self.big_blind)
                elif ai_player.make_decision_pre() == "Call":
                    call_amount = min(self.highest_bet, ai_player.chips)
                    ai_player.current_bet = call_amount
                    ai_player.chips -= call_amount
                    self.pot += call_amount
                    return call_amount
                else:
                    self.players[1].fold_hand()
            

    def both_check(self):
        if not self.flop_dealt:
            self.deal_community_cards(3)
        elif not self.turn_dealt:
            self.deal_community_cards(1)
        elif not self.river_dealt:
            self.deal_community_cards(1)
        else:
            self.showdown()

    def get_preflop_odds(self, card1, card2):
        conn = sqlite3.connect('poker_odds.db')
        cursor = conn.cursor()
        if card1.suit == card2.suit:
            cursor.execute("SELECT win_rate FROM Preflop WHERE card1 = ? AND card2 = ?", (Card(card1.value, '♠'), Card(card2.value, '♠')))
            win_rate = cursor.fetchone()
            print(win_rate)
            conn.close()
            return win_rate[0] if win_rate else 0
        else:
            cursor.execute("SELECT win_rate FROM Preflop WHERE card1 = ? AND card2 = ?", (Card(card1.value, '♠'), Card(card2.value, '♥')))
            win_rate = cursor.fetchone()
            print(win_rate)
            conn.close()
            return win_rate[0] if win_rate else 0
        

    def state_of_game(self):
        game_state = super().get_game_state()
        card1, card2 = self.players[0].hand
        game_state["player1"]["preflop_odds"] = self.get_preflop_odds(card1.rank.value, card2.rank.value)
        return game_state

def main():
    player1 = Player("Alice", 10000)
    player2 = Player("Bob", 10000)
    game = PokerGame([player1, player2], big = 100)
    game.play_round()

if __name__ == "__main__":
    main()