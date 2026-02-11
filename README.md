# RTM

## General Usage
New moderators need to request the existing moderator Google account or alternatively set up Google Drive API and Gmail API, as well as replace the 5 links and 2 paths with the correct ones for their own game.  
Also required to get or create files for google_API_credentials_path and mod_email_app_password_path to use Google APIs  
Make sure there is a Google Form for players to submit their actions with the same questions as headers in the actions spreadsheet. Limit to 1 response needs to be off.  
- Collect game interest and populate the "Name" and "Email" columns of the "RTM Role Assignments" Google Sheet and the "Voting Player" column of the "Voting" Google Sheet
- Copy the list of player names into the "Name", "Who do you want to target with your night action", and "Who do you want your second target to be" sections of the "RTM Night Action" Google Form  
- Fill in the "Role Distribution Category" column of the "Role Distribution" Google Sheet with the desired role distribution categories (be sure to include 1 Godfather) (be sure to include 1 cop and 1 framer, unless you want to enforce the framer-cop dependency in the role assignment step instead)  
- Copy the list of role categories in the game and send it to the players  
- Navigate to *\RTM and run "streamlit run Mod_App.py" to open the moderator app  
- Go to the Role Distribution page, randomly create the actual role distribution, and manually edit it to balance the game as needed  
- Go to the Role Assignments page, randomly assign roles, and manually edit it to balance the game as needed  
- Go to the Email Roles page, preview roles to make sure everything looks correct, and send roles to the players  
- During each night, go to the Run Night Actions page, preview results to make sure everything looks correct, and send them to the players  
- During each voting phase, go to the Run Voting page, preview results to make sure everything looks correct, and send them to the players  
- If a mayor wants to reveal themselves, go to the Utilities page, type in their name, and click reveal mayor
- If a new Godfather needs to be assigned, at the appropriate time outlined in the rules, go to the Utilities page, check that there is an eligible player specified in the "New Godfather" Google Sheet, then click assign new Godfather

**Important:** For all steps detailed ("Voting Player" column of the "Voting" Google Sheet, players' votes in the "Voting" Google Sheet, mayor reveal, and new Godfather), the spelling and capitalization of players' names need to be identical to their names in the game_state files (which is derived from the "RTM Role Assignments" Google Sheet)

## Detailed Breakdown
### Automated moderation of real-time mafia  
The program contains 3 Python files and a blank actions csv file.  

Ask the previous mod for the mod email and password, along with the mod email related files
No longer needed: (It also requires setting up a Google Drive API in order to pull data from Google Sheets (needed for player data, role assignments, night actions, voting, and assigning new godfathers). Will need a .json file with credentials to use the API. (https://docs.gspread.org/en/latest/oauth2.html to set up Google Drive API)  

Additionally, it requires setting up 2-factor authentication and an app password with a Gmail account in order to automate emails. I store Gmail username and app password in a mod_email_app_password.csv file with headers of "email", and "app_password" and data in their respective columns. (Adapted from https://stackoverflow.com/questions/10147455/how-to-send-an-email-with-gmail-as-provider-using-python/27515833#27515833 and https://mailtrap.io/blog/python-send-email/)  
In Game.py, there are links to the 5 different Google Sheets files that are used in various stages of the game. They will need to be replaced with the corresponding links in each game.)

Roles.py file contains:  
  - Wrappers to ensure proper targeting by players  
  - A Role class that is inherited by all other classes and contains:  
    - Default attributes to be overwritten in special cases  
    - Default initializer  
    - Default functions all roles will need  
  - Town, Mafia, and Neutral classes, which inherit attributes from Role  
  - Multi-role class definitions for any roles that are identical between Town and Mafia roles  
  - Each role's class definition:  
    - Inherit their factions class (and the Role class by extension) and a multi-role class if applicable  
    - Have any unique attributes specific to the role  
    - Defined night actions  

Game.py file contains:  
  - 5 different Google Sheets files that are used in various stages of the game. They will need to be replaced with the corresponding links in each game  
  - Functions to interact with the related Google Sheets and the .csv files that they are read into  
  - A function to send emails to players with game updates and results  
  - A Game class which contains:  
      - Attributes used within the function in the class  
      - A randomize_roles function that randomly designates roles based on the given distribution
      - An assign_roles function that randomly assigns roles to players (NOT USED in the current implementation; this logic is pushed to the Streamlit app)
      - An email_roles function to email the players their roles
      - An email_roles_preview function to create a dataframe of Name, Email, Role, Email Preview, and Email Subject for each player and the group mafia email
      - A run_night function that takes the most recent game state and players' submitted actions to find the resulting game state and send results to players  
      - A run_voting function that takes the most recent game state, reads the voting Google Sheet to find the resulting game state, and sends results to players  
      - An assign_new_godfather function that takes the most recent game state and reads the new godfather Google Sheet to set the new godfather
      - A reveal_mayor function that takes the most recent game state and a player name who wants to reveal themselves as mayor, and sends that decision to players  
Mod_App.py file contains:
  - Overview page that  
  - Role Distribution page that loads the role distribution from the "RTM Role Distribution" Google Sheet and allows the moderator to randomly create distributions of those role categories and manually change them, then repopulates the "RTM Role Distribution" Google Sheet  
  - Role Assignment page that loads player info from the "RTM Role Assignments" Google Sheet and allows the moderator to randomly assign roles and manually change them, then repopulates the "RTM Role Assignments" Google Sheet  
  - Email Roles page that first shows a preview of the emails sent to each player and the mafia group, and then sends those emails out  
  - Run Night Actions page that first shows a preview of the emails each player will get sent based on the results of the night, and then sends those emails out  
  - Run Voting page that first shows a preview of the number of votes each player got and what the result of the vote would be, and then sends the public email out  
  - Utilities page that allows the moderator to reveal the mayor and elect new Godfathers
  - View Files page that lets the moderator view any game file
  - Restart Game page that allows the moderator to restart the game by deleting all associated game files

### Google Sheet Setup
The service account email needs to have editor permission on each Google Sheet (The email in the JSON next to "client_email:"
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

Categories should be one of ('Town Investigative', 'Town Killing', 'Town Support', 'Town Random', 'Mafia', 'Neutral', 'Godfather', 'Detective', 'Cop', 'Tracker', 'Watcher', 'Vigilante', 'Bodyguard', 'Veteran', 'Bomb', 'Mayor', 'Bus_driver', 'Escort', 'Doctor', 'Godfather', 'Lookout', 'Framer', 'Sniper', 'Yakuza', 'Janitor', 'Limo_driver', 'Hooker', 'Stalker', 'Sniper', 'Saboteur', 'Amnesiac', 'Arsonist', 'Jester', 'Witch', 'Serial_killer', 'Survivor', 'Mass_murderer')

Actions file: (The headers row specifically needs to NOT be frozen, or clearing data after a night will not work)
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

### Updates Needed
 - Does not check for the requirement of framer needing a cop to be in the game
 - The new godfather Google Sheet is not automatically sent out, which will be a problem if there is no moderator
