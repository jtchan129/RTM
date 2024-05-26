import sys
from Game import *




def main():
    game = Game()

    if len(sys.argv) != 2:
        print("Usage: python main.py <mode>")
        print("<mode> should be 'start_game', 'run_night', 'run_voting, or new_godfather")
        sys.exit(1)
    mode = sys.argv[1]

    # Only need to run a single time at the beginning of the game
    if mode == 'start_game':
        game.start_game()

    # Run this each night
    elif mode == 'run_night':
        game.run_night()
    
    # Run this to process voting
    elif mode == 'run_voting':
        game.run_voting()

    elif mode == 'new_godfather':
        game.assign_new_godfather()
        
    else:
        print("Invalid mode. Choose 'start_game', 'run_night', 'run_voting, or new_godfather")
        sys.exit(1)





if __name__ == '__main__':
    main()
