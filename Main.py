import sys
from Game import *


def main():
    game = Game()

    if len(sys.argv) != 2:
        print("Usage: python main.py <mode>")
        print("<mode> should be 'randomize_roles', 'assign_roles', 'email_roles', 'run_night', 'run_voting, or new_godfather")
        sys.exit(1)
    mode = sys.argv[1]

    # Only need to run a single time at the beginning of the game
    if mode == 'randomize_roles':
        game.randomize_roles()

    elif mode == 'assign_roles':
        game.assign_roles()

    elif mode == 'email_roles':
        game.email_roles()

    # Run this each night
    elif mode == 'run_night':
        game.run_night()
    
    # Run this to process voting
    elif mode == 'run_voting':
        game.run_voting()

    elif mode == 'new_godfather':
        game.assign_new_godfather()

    elif mode == 'reveal_mayor':
        mayor_name = input('Which player is revealing as mayor?: ')
        game.reveal_mayor(mayor_name)
        
    else:
        print("Invalid mode. Choose 'randomize_roles', 'assign_roles', 'email_roles', 'run_night', 'run_voting, or new_godfather")
        sys.exit(1)



if __name__ == '__main__':
    main()
