# RTM
### Automated moderation of real-time mafia  
The program contains 3 Python files, and a blank actions csv file.  

Ask the previous mod for the mod email and password along with the mod email related files
No longer needed: (It also requires setting up a Google Drive API in order to pull data from Google Sheets (needed for player data, role assignments, night actions, voting, and assigning new godfathers). Will need a .json file with credentials to use the API. (https://docs.gspread.org/en/latest/oauth2.html to set up Google Drive API)  

Additionally requires setting up 2-factor authentication and an app password with a Gmail account in order to automate emails. I store Gmail username and app password in a mod_email_app_password.csv file with headers of "email", and "app_password" and data in their respective columns. (Adapted from https://stackoverflow.com/questions/10147455/how-to-send-an-email-with-gmail-as-provider-using-python/27515833#27515833 and https://mailtrap.io/blog/python-send-email/)  
In Game.py there are links to the 5 different Google Sheets files that are used in various stages of the game. They will need to be replaced with the corresponding links in each game.)

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

Game.py file contains:  
  - 5 different Google Sheets files that are used in various stages of the game. They will need to be replaced with the corresponding links in each game  
  - Functions to interact with the related Google Sheets and the .csv files that they are read into  
  - A function to send emails to players with game updates and results  
  - A Game class which contains:  
      - Attributes used within the function in the class  
      - A randomize_roles function to only be run at the start of the game that randomly designated roles based on the given distribution
      - An assign_roles function to only be run at the start of the game that randomly assigns roles to players (So the assigned roles can be manually changed after randomize_roles if wanted)
      - An email_roles function to only be run at the start of the game that email the players their roles (So roles can be manually changed after assign_roles if wanted)
      - A run_night function that takes the most recent game state and players submitted actions to find the resulting game state and send results to players  
      - A run_voting function that takes the most recent game state and reads the voting Google Sheet to find the resulting game state and send results to players  
      - An assign_new_godfather function that takes the most recent game state and reads the new godfather Google Sheet to set the new godfather
      - A reveal_mayor function that takes the most recent game state and a player name who wants to reveal themselves as mayor and sends that decision to players  
Main.py file contains:
  - A menu to accept input from the user to select which function from Game.py to run

### Google Sheet Setup
The service account email needs to have editor permission on each google sheet (The email in the json next to "client_email:"
The associated Google Sheets should be formatted as follows:
Players file:
| Name         | Email          | Role          |
| ------------ | -------------- | ------------- |
| Example name | Example email  | Empty         |
| Example name | Example email  | Empty         |

Role Distribution file:
| Role Distribution Category | Actual Role Distribution |
| ------------ | -------------- |
| Example category | Empty |
| Example category | Empty |

Actions file: (The headers row specifically needs to NOT be frozen or clearing data after a night will not work)
| Timestamp | Email | Name | Who do you want to target with your night action | Who do you want your second target to be | Arsonist only: 'Douse', 'Undouse', or 'Ignite' |
|--- | --- | --- | --- |--- |--- |
| Empty | Empty | Empty | Empty | Empty | Empty |

Voting file:
| Voting Player | Day 1 | Day 2 | Day 3 | Ect... |
|--- | --- | --- | --- |--- |
| Example name | Empty | Empty | Empty | Empty |
| Example name | Empty | Empty | Empty | Empty |
| Ect... | Empty | Empty | Empty | Empty |

New Godfather file:
| New godfather | Empty |
| ------------ | -------------- |
| Where the new godfather will be put | Empty |
| Empty | Empty |

### Usage
New moderators need to set up google drive API and Gmail API as well as replace the 5 links and 2 paths with the correct ones for their own game.  
Make sure there is a google form for players to submit their actions with the same questions as headers in the actions spreadsheet. Limit to 1 response needs to be off.
- Run start_game to begin the game and assign roles  
- Run run_night to process each night  
- Run run_voting after votes are in each day  
- Run new_godfather right before voting if there is no godfather (make sure the mafia knows they need to fill out the corresponding sheet)  
- Run reveal_mayor whenever someone messages you they want to reveal as a mayor  

### Updates Needed
 - Does not check for the requirement of framer needing a cop to be in the game
 - The new godfather google sheet is not automatically sent out which will be a problem if there is no moderator
