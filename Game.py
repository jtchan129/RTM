import pandas as pd
from Roles import *
from pydrive.auth import GoogleAuth 
from pydrive.drive import GoogleDrive 
from collections import defaultdict
import os
import random
import smtplib
from email.mime.text import MIMEText


# Taken from URL's of corresponding role assignments, night actions, and voting spreadsheets
players_link_id = '1Xx1eEDy7PN5LafDeyJ0hxnFAY9LCWgU6vyC0E9detuU'
role_distribution_link_id = '1RLU1KegpTHqnU3Si2SLHGI5_XSaZLiP86VOohy9c7NI'
actions_link_id = '13lOQq90paeseCAJBkM4p-F2mln9_xhCyT1fcF7IGPho'
voting_link_id = '1P1mEFeEJhPkXKkgFxO6FNVyWyy2p37jMA03VQBvBX8Q'
newGF_link_id = '1rVmFK2hs9-VrTkXetdD_IKtnbygOd7TMU5acCGALFxg'


# Taken and adapted from https://www.geeksforgeeks.org/collecting-data-with-google-forms-and-pandas/
def pull_data(file_id, file_name):
    gauth = GoogleAuth()

    # Added this code segment to not require logging in through browser each time
    ###########################################
    gauth.LoadCredentialsFile("credentials.json")
    
    if gauth.credentials is None or gauth.access_token_expired:
        gauth.LocalWebserverAuth()
        gauth.SaveCredentialsFile("credentials.json")
    else:
        gauth.Authorize()
    ###########################################
    
    drive = GoogleDrive(gauth)
    
    # Initialize GoogleDriveFile instance with file id
    file_obj = drive.CreateFile({'id': file_id})
    file_obj.GetContentFile(file_name, mimetype='text/csv')
    
    dataframe = pd.read_csv(file_name)

    return dataframe


# Mode should be 'night'. 'day', or newGF
def find_last_file(mode):
    time_files = [file for file in os.listdir() if file.startswith('game_state') and f'{mode}' in file and file.endswith('.csv')]
    time_numbers = [int(f.split(mode)[-1].split('.csv')[0]) for f in time_files]

    files = [file for file in os.listdir() if file.startswith('game_state') and file.endswith('.csv')]
    numbers = [int(f.split('state')[-1].split('_', 2)[0]) for f in files]
    if numbers and time_numbers:
        max_index = numbers.index(max(numbers))
        return max(numbers), files[max_index], max(time_numbers)
    elif numbers:
        max_index = numbers.index(max(numbers))
        return max(numbers), files[max_index], 0
    elif time_numbers:
        return 0, None, max(time_numbers)
    else:
        print('Something went wrong in finding a file')

# Adapted from https://stackoverflow.com/questions/10147455/how-to-send-an-email-with-gmail-as-provider-using-python/27515833#27515833 and https://mailtrap.io/blog/python-send-email/
def send_email(receiver_email, message_text_list, subject):
    dataframe = pd.read_csv('mod_email_app_password.csv')
    sender_email = dataframe.loc[0, 'email']
    sender_app_password = dataframe.loc[0, 'app_password']

    smtpserver = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtpserver.ehlo()
    smtpserver.login(sender_email, sender_app_password)

    message_text = ''
    for text in message_text_list:
        message_text = message_text + ' ' + text

    # Create MIMEText object
    message = MIMEText(message_text, "plain")
    message["Subject"] = subject
    message["From"] = sender_email

    # Join emails if sending to mutiple
    if isinstance(receiver_email, str):
        message["To"] = receiver_email
    elif isinstance(receiver_email, list):
        message['To'] = ', '.join(receiver_email)

    smtpserver.sendmail(sender_email, receiver_email, message.as_string())

    # Close the connection
    smtpserver.close()


class Game:

    def __init__(self):
        self.rtm_group_email = []
        self.state_num = None
        self.night_num = None
        self.state_df = None
        self.actions_df = None
        self.voting_df = None
        self.player_dict = {}
        self.public_result = ''

    # start_game, run_night, and run_voting are independent of each other: They are never run on the same game object they individually interact with the game_state.csv file
    def start_game(self):
        # Load file of player names, emails and role distribution from google drive
        pull_data(players_link_id, 'game_state0_day0.csv')
        temp_role_dist_df = pull_data(role_distribution_link_id, 'role_distribution.csv')
        # Selecting only the first two columns and only keeping rows with values in the 'Role Distribution Category' column
        role_dist_df = temp_role_dist_df[['Role Distribution Category', 'Actual Role Distribution']].dropna(subset=['Role Distribution Category'])

        # Randomly select role distribution based on categories
        town_investigative_list = ['Detective', 'Cop', 'Tracker', 'Watcher']
        town_killing_list = ['Vigilante', 'Bodyguard', 'Veteran', 'Bomb']
        town_support_list = ['Mayor', 'Bus_driver', 'Escort', 'Doctor']
        town_random_list = ['Detective', 'Cop', 'Tracker', 'Watcher', 'Vigilante', 'Bodyguard', 'Veteran', 'Bomb', 'Mayor', 'Bus_driver', 'Escort', 'Doctor']
        mafia_list = ['Lookout', 'Framer', 'Sniper', 'Yakuza', 'Janitor', 'Limo Driver', 'Hooker', 'Stalker', 'Sniper', 'Saboteur']
        neutral_list = ['Amnesiac', 'Arsonist', 'Jester', 'Witch', 'Serial_killer', 'Survivor', 'Mass_murderer']
        # Used in removing unique roles
        role_lists_list = [town_investigative_list, town_killing_list, town_support_list, mafia_list, neutral_list]

        # This can be expanded later to put limits on the number of each role in the game
        unique_dict = {'Bomb': 1,
                       'Mayor': 1,
                       'Bus_driver': 1,
                       'Saboteur': 1,}
        
        role_assignments_list = []
        
        for index, row in role_dist_df.iterrows():
            if row['Role Distribution Category'] is not None:
                assigned_role = ''
                if row['Role Distribution Category'] == 'Godfather':
                    assigned_role = 'Godfather'
                elif row['Role Distribution Category'] == 'Town Investigative':
                    assigned_role = random.choice(town_investigative_list)
                elif row['Role Distribution Category'] == 'Town Killing':
                    assigned_role = random.choice(town_killing_list)
                elif row['Role Distribution Category'] == 'Town Support':
                    assigned_role = random.choice(town_support_list)
                elif row['Role Distribution Category'] == 'Town Random':
                    assigned_role = random.choice(town_random_list)
                elif row['Role Distribution Category'] == 'Mafia':
                    assigned_role = random.choice(mafia_list)
                elif row['Role Distribution Category'] == 'Neutral':
                    assigned_role = random.choice(neutral_list)
                else:
                    print('Error in assigning roles')
                
                for unique_role in unique_dict:
                    if assigned_role == unique_role:
                        unique_dict[unique_role] = unique_dict[unique_role] - 1
                    if unique_dict[unique_role] == 0:
                        for role_list in role_lists_list:
                            if unique_role in role_list:
                                role_list.remove(unique_role)

                role_dist_df.loc[index, 'Actual Role Distribution'] = assigned_role
                role_assignments_list.append(assigned_role)

        print(role_dist_df)

        # Add new columns for the night each player died, the number of times they have used their action, whether they are doused, whether they are sabotaged, and whether they are marked for death
        game_state_file = 'game_state0_day0.csv'
        temp_state_df = pd.read_csv(game_state_file)
        temp_state_df['Time died'] = 'Alive'
        temp_state_df['Actions used'] = 0
        temp_state_df['Doused'] = 0
        temp_state_df['Sabotaged'] = 0
        temp_state_df['Marked'] = 0

        # Populate the players roles randomly with the roles from the generated distribution
        random.shuffle(role_assignments_list)
        for index, row in temp_state_df.iterrows():
            temp_state_df.loc[index, 'Role'] = role_assignments_list[index]
        
        temp_state_df.to_csv(game_state_file, index=False)

        # Reupload the file to Google Drive
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile("credentials.json")
        
        if gauth.credentials is None or gauth.access_token_expired:
            gauth.LocalWebserverAuth()
            gauth.SaveCredentialsFile("credentials.json")
        else:
            gauth.Authorize()
            
        drive = GoogleDrive(gauth)
        
        file_obj = drive.CreateFile({'id': players_link_id})
        file_obj.SetContentFile('game_state0_day0.csv')
        file_obj.Upload()


    def run_night(self):
        # Find most recent game state number, game state number, and night number and set accordingly
        last_state_num, last_state_file, last_night_num = find_last_file('night')
        self.state_num = last_state_num + 1
        self.night_num =  last_night_num + 1

        # Load last game state file
        self.state_df = pd.read_csv(last_state_file)

        # Load file of night actions from google drive
        self.actions_df = pull_data(actions_link_id, 'actions_night' + str(self.night_num) + '.csv')

        # Creating set of play objects
        self.create_players()

        # Create the group email to send public results
        self.create_rtm_group_email()

        # Setting targets
        self.set_targets()

        # Run actions in priority order
        self.run_actions()

        # Send emails for each player's results
        self.email_results()

        # Process deaths
        self.process_deaths()

        # Update number of actions used
        self.update_state_file()

        # Clear the actions spreadsheet
        # self.clear_actions()

        # Send email to everyone with public result
        send_email(self.rtm_group_email, self.public_result, 'Night ' + str(self.night_num) + ' results')


    def run_voting(self):
        # Find most recent game state number, game state file name, and day number and set accordingly
        last_state_num, last_state_file, last_day_num = find_last_file('day')
        self.state_num = last_state_num + 1
        day_num = last_day_num + 1

        column_name = 'Day ' + str(day_num)

        # Load the last game state file
        self.state_df = pd.read_csv(last_state_file)

        # Create the group email to send public results
        self.create_rtm_group_email()

        self.voting_df = pull_data(voting_link_id, 'voting_day' + str(day_num) + '.csv')

        self.voting_df = self.voting_df[['Voting Player', column_name]]

        # Set any non-valid votes to blank
        for index, row in self.voting_df.iterrows():
            voting_player_alive = (row['Voting Player'] in self.state_df.loc[self.state_df['Time died'] == 'Alive', 'Name'].values)
            target_player_alive = (row[column_name] in self.state_df.loc[self.state_df['Time died'] == 'Alive', 'Name'].values) or row[column_name] == 'No vote'

            if not voting_player_alive or not target_player_alive:
                self.voting_df.loc[index, column_name] = ''
        
        # Determining execute and public message
        valid_votes = self.voting_df[self.voting_df[column_name] != ''][column_name]

        if len(valid_votes.mode()) > 1:
            self.public_result = 'On day ' + str(day_num) + ', the town of Pi voted to not execute anyone by tied vote'
        elif len(valid_votes.mode()) == 0 or valid_votes.mode()[0] == 'No vote':
            self.public_result = 'On day ' + str(day_num) + ', the town of Pi voted to not execute anyone by a no vote'
        else:
            most_voted = valid_votes.mode()[0]
            self.public_result = 'On day ' + str(day_num) + ', the town of Pi voted to execute ' + most_voted
            player_index = self.state_df[self.state_df['Name'] == most_voted].index
            self.state_df.loc[player_index, 'Time died'] = ('Day ' + str(day_num))

            # Checking for Jester or Saboteur deaths
            if self.state_df.loc[player_index, 'Role'].values[0] == 'Saboteur':
                self.state_df.loc[self.state_df['Sabotaged'] == 1, 'Marked'] = 1
            
            if self.state_df.loc[player_index, 'Role'].values[0] == 'Jester':
                jester_name = self.state_df.loc[player_index, 'Name']
                vote_list = self.voting_df[(self.voting_df[column_name] == most_voted) & (self.voting_df['Voting Player'] != jester_name.values[0])]['Voting Player'].tolist()
                if vote_list:
                    jester_target_name = random.choice(vote_list)
                    jester_target_index = self.state_df[self.state_df['Name'] == jester_target_name].index
                    self.state_df.loc[jester_target_index, 'Marked'] = 1

        
        send_email(self.rtm_group_email, self.public_result, 'Day ' + str(self.night_num) + ' execution results')

        self.state_df.to_csv('game_state' + str(self.state_num) + '_day' + str(day_num) + '.csv', index=False)

    # Might want to take the game_state file creation outside of the loop
    def assign_new_godfather(self):
        last_state_num, last_state_file, last_newGF_num = find_last_file('newGF')
        self.state_num = last_state_num + 1
        newGF_num = last_newGF_num + 1

        # Load the last game state file
        self.state_df = pd.read_csv(last_state_file)

        newGF_df = pull_data(newGF_link_id, 'newGF' + str(newGF_num) + '.csv')
        newGF_name = newGF_df.loc[0, 'New godfather']

        player_index = self.state_df[self.state_df['Name'] == newGF_name].index

        newGF_mafia_list = ['Mafioso', 'Limo_driver', 'Stalker', 'Lookout', 'Hooker', 'Janitor', 'Framer', 'Yakuza', 'Saboteur', 'Sniper']

        if self.state_df.loc[player_index, 'Role'].values[0] in newGF_mafia_list:
            self.state_df.loc[player_index, 'Role'] = 'Godfather'
            self.state_df.to_csv('game_state' + str(self.state_num) + '_newGF' + str(newGF_num) + '.csv', index=False)


    def create_rtm_group_email(self):
        for _, row in self.state_df.iterrows():
            email = row['Email']
            if email:
                self.rtm_group_email.append(email)
            else:
                print('Error in adding email')


    def create_players(self):
        self.player_dict = defaultdict(list)

        for _, row in self.state_df.iterrows():
            role_class = globals().get(row['Role'])
            if role_class:
                if row['Time died'] == 'Alive':
                    self.player_dict[role_class(name = row['Name'], email = row['Email'], player_dict = self.player_dict, dead = False, actions_used = row['Actions used'], doused = row['Doused'], sabotaged = row['Sabotaged'], marked = row['Marked'])] = []
                else:
                    self.player_dict[role_class(name = row['Name'], email = row['Email'], player_dict = self.player_dict, dead = True, actions_used = row['Actions used'])] = []
            else:
                print('Error in creating ' + row['Role'] + ' role')


    # This is probably not the best way to implement this
    def set_targets(self):
        for _, row in self.actions_df.iterrows():
            for player in self.player_dict:
                # Setting arsonist action choice
                if str(type(player).__name__) == 'Arsonist':
                    arsonist_action = row['Arsonist only: \'Douse\', \'Undouse\', or \'Ignite\'']
                    if arsonist_action == 'Undouse' or arsonist_action == 'Ignite':
                        player.arso_action = arsonist_action

                for target in self.player_dict:
                    if player.get_name() == row['Name'] and target.get_name() == row['Who do you want to target with your night action']:
                        player.select_target(target)

        for _, row in self.actions_df.iterrows():
            for player in self.player_dict:
                for target in self.player_dict:
                    if player.get_name() == row['Name'] and target.get_name() == row['Who do you want your second target to be']:
                        player.select_target2(target)


    def run_actions(self):
        priority_list = ['Bus_driver', 'Limo_driver', 'Veteran', 'Witch', 'Escort', 'Hooker', 'Framer', 'Cop', 'Detective', 'Doctor', 'Bodyguard', 'Survivor', 'Vigilante', 'Bomb', 'Godfather', 'Sniper', 'Mass_murderer', 'Serial_killer', 'Arsonist', 'Janitor', 'Tracker', 'Stalker', 'Watcher', 'Lookout', 'Saboteur', 'Amnesiac']
        end_priotity_list = ['Janitor', 'Bodyguard', 'Bomb', 'Doctor', 'Yakuza']

        for player in self.player_dict:
            if player.marked == 1:
                player.die()
                player.marked = 0

        # Running actions
        for priority in priority_list:
            for player in self.player_dict:
                if priority == str(type(player).__name__):
                    player.perform_action()

        # Running actions that need to be done at the end
        for priority in end_priotity_list:
            for player in self.player_dict:
                if priority == str(type(player).__name__):
                    player.end_action()

    
    def email_results(self):
        for player in self.player_dict:
            if player.dead == False and player.get_results():
                send_email(player.get_email(), player.get_results(), 'Night ' + str(self.night_num) + ' individual results')


    def process_deaths(self):
        self.public_result = 'In the town of Pi the villagers awoke after night ' + str(self.night_num)
        dead_list = []

        # Editing the state_df
        for player in self.player_dict:
            if player.died_tonight == True:
                player_index = self.state_df[self.state_df['Name'] == player.get_name()].index
                self.state_df.loc[player_index, 'Time died'] = 'Night ' + str(self.night_num)
                dead_list.append(player)

        # Preparing the public result
        if dead_list:
            self.public_result = self.public_result + ' and found '
            for i in range(len(dead_list)):
                if dead_list[i].cleaned == True:
                    self.public_result = self.public_result + dead_list[i].get_name() + ' the unknown (cleaned by janitor)'
                elif str(type(dead_list[i]).__name__) ==  'Yakuza':
                    self.public_result = self.public_result + dead_list[i].get_name() + ' the ' + dead_list[i].revealed_role
                else:
                    self.public_result = self.public_result + dead_list[i].get_name() + ' the ' + str(type(dead_list[i]).__name__)
                if i != len(dead_list) - 1:
                    self.public_result = self.public_result + ' and '
                else:
                    self.public_result = self.public_result + ' dead'

        else:
            self.public_result = self.public_result + ' to a peaceful morning'


    # Update the file to include the number of actions each player has used, if they are doused or not, and reset the sabogated player
    def update_state_file(self):
        for player in self.player_dict:
            player_index = self.state_df[self.state_df['Name'] == player.get_name()].index
            self.state_df.loc[player_index, 'Actions used'] = player.actions_used
            self.state_df.loc[player_index, 'Doused'] = player.doused
            self.state_df.loc[player_index, 'Sabotaged'] = player.sabotaged
            self.state_df.loc[player_index, 'Marked'] = 0

            # Checking for yakuza corruption
            if player.corrupted == True:
                self.state_df.loc[player_index, 'Role'] = 'Mafioso'

            # Checking for amnesiac remembering
            if str(type(player).__name__) == 'Amnesiac':
                if player.remembered_role != 'Amnesiac':
                    self.state_df.loc[player_index, 'Role'] = player.remembered_role
                    self.state_df.loc[player_index, 'Actions used'] = 0
                    self.public_result = self.public_result + 'An amnesiac remembered they were a ' + player.remembered_role

        self.state_df.to_csv('game_state' + str(self.state_num) + '_night' + str(self.night_num) + '.csv', index=False)

    
    def clear_actions(self):
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile("credentials.json")
        
        if gauth.credentials is None or gauth.access_token_expired:
            gauth.LocalWebserverAuth()
            gauth.SaveCredentialsFile("credentials.json")
        else:
            gauth.Authorize()
            
        drive = GoogleDrive(gauth)
        
        file_obj = drive.CreateFile({'id': actions_link_id})
        file_obj.SetContentFile('blank_actions.csv')
        file_obj.Upload()

    # Not currently being used
    def check_win_conditions(self):
        last_state_num, last_state_file, last_night_num = find_last_file('night')
        self.state_df = pd.read_csv(last_state_file)

        self.create_players()
        
        num_town = 0
        num_mafia = 0
        num_lethal_neutral = 0
        town_name_list = []
        mafia_name_list = []
        neutral_name_list = []
        witch_name_list = []
        survivor_name_list = []
        winner_list = []
        win_public_message = ''

        for player in self.player_dict:

            if player.faction == 'Town':
                town_name_list.append(str(type(player).__name__))
                if player.dead == False:
                    num_town += 1
            elif player.faction == 'Mafia':
                mafia_name_list.append(str(type(player).__name__))
                if player.dead == False:
                    num_mafia += 1
            elif player.faction == 'Lethal neutral' and player.dead == False:
                num_lethal_neutral += 1
                neutral_name_list.append(str(type(player).__name__))
            elif str(type(player).__name__) == 'Survivor' and player.dead == False:
                survivor_name_list.append(str(type(player).__name__))
            elif str(type(player).__name__) == 'Witch' and player.dead == False:
                witch_name_list.append(str(type(player).__name__))


        if num_mafia == 0 and num_lethal_neutral == 0 and num_town > 0:
            win_public_message = win_public_message + 'Town wins!'
            winner_list = town_name_list
        if num_mafia > num_town and num_lethal_neutral == 0 and num_mafia > 0:
            win_public_message = win_public_message + 'Mafia wins!'
            winner_list = mafia_name_list
        if num_mafia == 0 and num_town == 0 and num_lethal_neutral > 0:
            win_public_message = win_public_message + 'Neutral lethals win!'
            winner_list = neutral_name_list
            for witch_name in witch_name_list:
                winner_list.append(witch_name)

        for survivor_name in survivor_name_list:
            winner_list.append(survivor_name)

        win_public_message = win_public_message + ' Winners are: '
        for i in range(len(winner_list)):
            if i != len(winner_list) - 1:
                win_public_message = win_public_message + winner_list[i] + ', '
            else:
                win_public_message = win_public_message + 'and ' + winner_list[i]


