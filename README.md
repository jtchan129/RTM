# RTM
### Automated moderation of real-time mafia  
The program contains 3 Python files, and a blank actions csv file.  

It also requires setting up a Google Drive API in order to pull data from Google Sheets (needed for player data, role assignments, night actions, voting, and assigning new godfathers). Will need client_secrets.json and credentials.json files in the same folder. (https://www.geeksforgeeks.org/collecting-data-with-google-forms-and-pandas/ to set up Google Drive API)  

Additionally requires setting up 2-factor authentication and an app password with a Gmail account in order to automate emails. I store Gmail username and app password in a mod_email_app_password.csv file with headers of "email", and "app_password" and data in their respective columns. (Adapted from https://stackoverflow.com/questions/10147455/how-to-send-an-email-with-gmail-as-provider-using-python/27515833#27515833 and https://mailtrap.io/blog/python-send-email/)  
In Game.py there are links to the 5 different Google Sheets files that are used in various stages of the game. They will need to be replaced with the corresponding links in each game.  

Roles.py file contains:  
  - Wrappers to ensure proper targeting by players  
  - A Role class that is inherited by all other classes and contains:  
    - Default attributes to be overwritten in special cases  
    - Default initializer  
    - Default functions all roles will need  
  - Town, Mafia, and Neutral classes which inherit attributes from Role  
  - Multi-role class defenitions for any roles that are identical between Town and Mafia roles  
  - Each roles' class defenition which:  
    - Inherit their factions class (and the Role class by extension) and a multi-role class if applicable  
    - Have any unique attributes specific to the role  
    - Defined night actions  

Game.py file contrains:  
  - 5 different Google Sheets files that are used in various stages of the game. They will need to be replaced with the corresponding links in each game  
  - Functions to interact with the related Google Sheets and the .csv files that they are read into  
  - A function to send emails to players with game updates and results  
  - A Game class which contains:  
      - Attributes used within the function in the class  
      - A start_game function to only be run at the start of the game that randomly assigns roles to the players  
      - A run_night function that takes the most recent game state and players submitted actions to find the resulting game state and send results to players  
      - A run_voting function that takes the most recent game state and reads the voting Google Sheet to find the resulting game state and send results to players  
      - An assign_new_godfather function that takes the most recent game state and reads the new godfather Google Sheet to set the new godfather
      - A reveal_mayor function that takes the most recent game state and a player name who wants to reveal themselves as mayor and sends that decision to players
