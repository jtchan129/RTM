import pandas as pd
from Roles import *
import gspread
from collections import defaultdict
import os
import random
import smtplib
from email.mime.text import MIMEText


# These are the fields that need to be changed before the start of a game
#####################################################################################################################
players_link_id = '1q-C1SNAMmPUx__y5gxaviZFv1e-BiMeUH9TQUxmvxmE'
role_distribution_link_id = '1tGCLbzXLsFyG4JRi0D2SRUeCFSLCN5IeUXZzHj-BCC4'
actions_link_id = '1qZfl1y6T73z_AKxu_1WhrR0Q1AgfvttBSzqOMVwvJiI'
voting_link_id = '1rdUudou9gnQO_P-dYSss-Sp8lCxWZPpLx-S-Bnko2UM'
newGF_link_id = '1eFGj0u9iAy7FBw0lMS96sdWwobCyrHaAZ21prVnbO88'

google_API_credentials_path = 'real-time-mafia-175d61ce3729.json'
mod_email_app_password_path = 'mod_email_app_password.csv'
#####################################################################################################################

# Takes a Google Sheets file ID and a name for the .csv file the data will be saved to
# Taken and adapted from https://docs.gspread.org/en/latest/oauth2.html and https://docs.gspread.org/en/latest/user-guide.html#using-gspread-with-pandas
def pull_data(file_id, file_name):
    gc = gspread.service_account(filename=google_API_credentials_path)

    sheet = gc.open_by_key(file_id)
    worksheet = sheet.get_worksheet(0)

    dataframe = pd.DataFrame(worksheet.get_all_records())

    dataframe.to_csv(file_name, index=False)

    return dataframe, worksheet

# Reupload the file to Google Drive
def update_file(dataframe, worksheet):
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

# Remove all data besides headers from a sheet
def clear_data(worksheet, confirm=False):
    # Ask the user for confirmation
    if confirm:
        send_confirmation = input('Would you like to clear the actions sheet? (yes/no): ').strip().lower()
        
        if send_confirmation != 'yes':
            print('Sheet not cleared')
            return
    worksheet.resize(rows=1)
    worksheet.resize(rows=150)
    print('Sheet cleared')

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
def send_email(receiver_email, message_text_list, subject, confirm = False):
    message_text = ''
    for text in message_text_list:
        message_text = message_text + ' ' + text

    # Ask the user for confirmation
    if confirm:
        print(f'Message text:\n{message_text}')
        
        send_confirmation = input('Would you like to send the email? (yes/no): ').strip().lower()
        
        if send_confirmation != 'yes':
            print('Email not sent')
            return
    
    dataframe = pd.read_csv(mod_email_app_password_path)
    sender_email = dataframe.loc[0, 'email']
    sender_app_password = dataframe.loc[0, 'app_password']

    smtpserver = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtpserver.ehlo()
    smtpserver.login(sender_email, sender_app_password)

    # Create MIMEText object
    message = MIMEText(message_text, 'plain')
    message['Subject'] = subject
    message['From'] = sender_email

    # Join emails if sending to mutiple
    if isinstance(receiver_email, str):
        message['To'] = receiver_email
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

    # ranodmize_roles, assign_roles, run_night, and run_voting are independent of each other: They are never run on the same game object they individually interact with the game_state.csv file
    def randomize_roles(self):
        # Load role distribution from google drive
        role_dist_df, role_dist_worksheet = pull_data(role_distribution_link_id, 'role_distribution.csv')

        # Randomly select role distribution based on categories
        town_investigative_list = ['Detective', 'Cop', 'Tracker', 'Watcher']
        town_killing_list = ['Vigilante', 'Bodyguard', 'Veteran', 'Bomb']
        town_support_list = ['Mayor', 'Bus_driver', 'Escort', 'Doctor']
        town_random_list = ['Detective', 'Cop', 'Tracker', 'Watcher', 'Vigilante', 'Bodyguard', 'Veteran', 'Bomb', 'Mayor', 'Bus_driver', 'Escort', 'Doctor']
        mafia_list = ['Lookout', 'Framer', 'Sniper', 'Yakuza', 'Janitor', 'Limo_driver', 'Hooker', 'Stalker', 'Sniper', 'Saboteur']
        neutral_list = ['Amnesiac', 'Arsonist', 'Jester', 'Witch', 'Serial_killer', 'Survivor', 'Mass_murderer']
        # Used to assign specific roles
        full_roles_list = ['Detective', 'Cop', 'Tracker', 'Watcher', 'Vigilante', 'Bodyguard', 'Veteran', 'Bomb', 'Mayor', 'Bus_driver', 'Escort', 'Doctor', 'Godfather', 'Lookout', 'Framer', 'Sniper', 'Yakuza', 'Janitor', 'Limo_driver', 'Hooker', 'Stalker', 'Sniper', 'Saboteur', 'Amnesiac', 'Arsonist', 'Jester', 'Witch', 'Serial_killer', 'Survivor', 'Mass_murderer']
        # Used in removing unique roles
        role_lists_list = [town_investigative_list, town_killing_list, town_support_list, town_random_list, mafia_list, neutral_list, full_roles_list]

        # This can be expanded later to put limits on the number of each role in the game
        unique_dict = {'Bomb': 1,
                       'Mayor': 1,
                       'Bus_driver': 1,
                       'Limo_driver': 1,
                       'Sniper': 1,
                       'Saboteur': 1,
                       "Amnesiac": 1}
        
        role_assignments_list = []
        
        for index, row in role_dist_df.iterrows():
            if row['Role Distribution Category'] is not None:
                assigned_role = ''
                if row['Role Distribution Category'] == 'Town Investigative':
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
                elif row['Role Distribution Category'] in full_roles_list:
                    assigned_role = row['Role Distribution Category']
                else:
                    print('Error in generating roles')
                
                for unique_role in unique_dict:
                    if assigned_role == unique_role:
                        unique_dict[unique_role] = unique_dict[unique_role] - 1
                    if unique_dict[unique_role] == 0:
                        for role_list in role_lists_list:
                            if unique_role in role_list:
                                role_list.remove(unique_role)

                role_dist_df.loc[index, 'Actual Role Distribution'] = assigned_role
                role_assignments_list.append(assigned_role)

        role_dist_df.to_csv('role_distribution.csv', index=False)
        update_file(role_dist_df, role_dist_worksheet)

    # Assign players roles based on the role distribution
    def assign_roles(self):
        state_df, state_worksheet = pull_data(players_link_id, 'game_state0_day0.csv')
        role_dist_df, _ = pull_data(role_distribution_link_id, 'role_distribution.csv')
        role_assignments_list = role_dist_df['Actual Role Distribution'].tolist()
        
        state_df['Time died'] = 'Alive'
        state_df['Actions used'] = 0
        state_df['Doused'] = 0
        state_df['Sabotaged'] = 0
        state_df['Marked'] = 0
        state_df['Revealed Mayor'] = 0

        # Populate the players roles randomly with the roles from the generated distribution
        random.shuffle(role_assignments_list)
        for index, row in state_df.iterrows():
            state_df.loc[index, 'Role'] = role_assignments_list[index]

        # Saving roles in csv and Google Sheets
        state_df.to_csv('game_state0_day0.csv', index=False)
        update_file(state_df[['Name', 'Email', 'Role']], state_worksheet)

    # Send emails informing people of their roles
    def email_roles(self):
        state_df, _ = pull_data(players_link_id, 'game_state0_day0.csv')
        
        revealed_mafia_list = ['Godfather', 'Lookout', 'Framer', 'Sniper', 'Yakuza', 'Janitor', 'Limo_driver', 'Hooker', 'Stalker', 'Sniper']
        mafia_emails = []
        mafia_message = ['The mafia members are']
        for index, row in state_df.iterrows():
            email_message = 'Your role is ' + row['Role']
            email_subject = 'RTM Role Assignments'
            send_email(row['Email'], email_message, email_subject)
            if row['Role'] in revealed_mafia_list:
                mafia_emails.append(row['Email'])
                mafia_message.append(row['Name'])
                
        gf_sheet_link = f"https://docs.google.com/spreadsheets/d/{newGF_link_id}"
        mafia_message.append(f"\n\nThe new Godfather Google Sheet is: {gf_sheet_link}")
        mafia_subject = 'Mafia members'
        send_email(mafia_emails, mafia_message, mafia_subject)

        state_df['Time died'] = 'Alive'
        state_df['Actions used'] = 0
        state_df['Doused'] = 0
        state_df['Sabotaged'] = 0
        state_df['Marked'] = 0
        state_df['Revealed Mayor'] = 0

        # Saving roles to csv again in case they were manually changed in the Google sheet
        state_df.to_csv('game_state0_day0.csv', index=False)

    def run_night(self):
        # Find most recent game state number, game state number, and night number and set accordingly
        last_state_num, last_state_file, last_night_num = find_last_file('night')
        self.state_num = last_state_num + 1
        self.night_num =  last_night_num + 1

        # Load last game state file
        self.state_df = pd.read_csv(last_state_file)

        # Load file of night actions from google drive
        self.actions_df, actions_worksheet = pull_data(actions_link_id, 'actions_night' + str(self.night_num) + '.csv')

        # Taking only the most recent action for each player
        self.actions_df['Timestamp'] = pd.to_datetime(self.actions_df['Timestamp'])
        self.actions_df = self.actions_df.sort_values(by='Timestamp').drop_duplicates(subset=['Name'], keep='last')
        self.actions_df.to_csv('actions_night' + str(self.night_num) + '.csv', index=False)

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

        # Send email to everyone with public result
        send_email(self.rtm_group_email, self.public_result, 'Night ' + str(self.night_num) + ' results', confirm = True)
        
        # Clear the actions spreadsheet
        clear_data(actions_worksheet)


    def run_voting(self):
        # Find most recent game state number, game state file name, and day number and set accordingly
        last_state_num, last_state_file, last_day_num = find_last_file('day')
        self.state_num = last_state_num + 1
        day_num = last_day_num + 1

        day_column_name = 'Day ' + str(day_num)

        # Load the last game state file
        self.state_df = pd.read_csv(last_state_file)

        # Create the group email to send public results
        self.create_rtm_group_email()

        self.voting_df, voting_worksheet = pull_data(voting_link_id, 'voting_day' + str(day_num) + '.csv')

        self.voting_df = self.voting_df[['Voting Player', day_column_name]]

        # Making voting non-case sensitive
        # self.state_df['Name'] = self.state_df['Name'].str.lower()

        # self.voting_df['Voting Player'] = self.voting_df['Voting Player'].str.lower()
        # self.voting_df[day_column_name] = self.voting_df[day_column_name].str.lower()

        # Set any non-valid votes to blank
        for index, row in self.voting_df.iterrows():
            voting_player_alive = (row['Voting Player'] in self.state_df.loc[self.state_df['Time died'] == 'Alive', 'Name'].values)
            target_player_alive = (row[day_column_name] in self.state_df.loc[self.state_df['Time died'] == 'Alive', 'Name'].values) or row[day_column_name] == 'No vote'

            if not voting_player_alive or not target_player_alive:
                self.voting_df.loc[index, day_column_name] = ''

        valid_votes_df = self.voting_df[self.voting_df[day_column_name] != ''][['Voting Player', day_column_name]]

        # Creating a dictionary to count votes
        voting_keys = list(self.state_df['Name'])
        voting_dict = {key: 0 for key in voting_keys}
        voting_dict['No vote'] = 0

        for _, row in valid_votes_df.iterrows():
            if self.state_df.loc[self.state_df['Name'] == row['Voting Player'], 'Revealed Mayor'].values == 1:
                voting_dict[row[day_column_name]] = voting_dict[row[day_column_name]] + 3
            else:
                voting_dict[row[day_column_name]] = voting_dict[row[day_column_name]] + 1
        
        # Take the counts of votes and sort them to later find the maximum
        vote_counts = list(voting_dict.values())
        vote_counts.sort(reverse=True)

        # Determining execute and public message
        if vote_counts[0] == 0:
            self.public_result = 'On day ' + str(day_num) + ', the town of Pi voted to not execute anyone by a no vote'
        elif vote_counts[0] == vote_counts[1]:
            self.public_result = 'On day ' + str(day_num) + ', the town of Pi voted to not execute anyone by tied vote'
        else:
            most_voted = None
            for voted_player, num_votes in voting_dict.items():
                if num_votes == vote_counts[0]:
                    most_voted = voted_player
            # Getting voted player's role
            most_voted_role = self.state_df.loc[self.state_df['Name'] == most_voted, 'Role'].values[0]

            if most_voted == 'No vote':
                self.public_result = 'On day ' + str(day_num) + ', the town of Pi voted to not execute anyone by a no vote'
            else:
                self.public_result = 'On day ' + str(day_num) + ', the town of Pi voted to execute ' + most_voted + ' the ' + most_voted_role
                player_index = self.state_df[self.state_df['Name'] == most_voted].index
                self.state_df.loc[player_index, 'Time died'] = ('Day ' + str(day_num))

                # Checking for Jester or Saboteur deaths
                if self.state_df.loc[player_index, 'Role'].values[0] == 'Saboteur':
                    self.state_df.loc[self.state_df['Sabotaged'] == 1, 'Marked'] = 1
                
                if self.state_df.loc[player_index, 'Role'].values[0] == 'Jester':
                    jester_name = self.state_df.loc[player_index, 'Name']
                    vote_list = self.voting_df[(self.voting_df[day_column_name] == most_voted) & (self.voting_df['Voting Player'] != jester_name.values[0])]['Voting Player'].tolist()
                    if vote_list:
                        jester_target_name = random.choice(vote_list)
                        jester_target_index = self.state_df[self.state_df['Name'] == jester_target_name].index
                        self.state_df.loc[jester_target_index, 'Marked'] = 1

        send_email(self.rtm_group_email, self.public_result, 'Day ' + str(day_num) + ' execution results', confirm=True)

        self.state_df.to_csv('game_state' + str(self.state_num) + '_day' + str(day_num) + '.csv', index=False)


    def assign_new_godfather(self):
        last_state_num, last_state_file, last_newGF_num = find_last_file('newGF')
        self.state_num = last_state_num + 1
        newGF_num = last_newGF_num + 1

        # Load the last game state file
        self.state_df = pd.read_csv(last_state_file)

        newGF_df, _ = pull_data(newGF_link_id, 'newGF' + str(newGF_num) + '.csv')
        newGF_name = newGF_df.loc[0, 'New godfather']

        player_index = self.state_df[self.state_df['Name'] == newGF_name].index

        newGF_mafia_list = ['Mafioso', 'Limo_driver', 'Stalker', 'Lookout', 'Hooker', 'Janitor', 'Framer', 'Yakuza', 'Saboteur', 'Sniper']

        if self.state_df.loc[player_index, 'Role'].values[0] in newGF_mafia_list:
            self.state_df.loc[player_index, 'Role'] = 'Godfather'
            self.state_df.to_csv('game_state' + str(self.state_num) + '_newGF' + str(newGF_num) + '.csv', index=False)
            # Sending email
            newGF_email = self.state_df.loc[player_index[0], 'Email']
            subject = "You Are the New Godfather"
            message_text_list = ["You have been chosen as the new Godfather."]
            send_email(newGF_email, message_text_list, subject)

    
    def reveal_mayor(self, mayor_name):
        last_state_num, last_state_file, last_reveal_num = find_last_file('reveal')
        self.state_num = last_state_num + 1
        reveal_num = last_reveal_num + 1

        # Load the last game state file
        self.state_df = pd.read_csv(last_state_file)

        self.create_rtm_group_email()

        player_index = self.state_df[self.state_df['Name'] == mayor_name].index

        if len(player_index) == 0:
            print('Name not found')
            return

        if self.state_df.loc[player_index, 'Role'].values[0] == 'Mayor':
            self.state_df.loc[player_index, 'Revealed Mayor'] = 1
            
            send_email(self.rtm_group_email, mayor_name + ' has revealed themselves as mayor', 'Mayor reveal')
            self.state_df.to_csv('game_state' + str(self.state_num) + '_reveal' + str(reveal_num) + '.csv', index=False)
        else:
            print('Player is not a mayor')


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
                    self.player_dict[role_class(name = row['Name'], email = row['Email'], player_dict = self.player_dict, dead = False, actions_used = row['Actions used'], doused = row['Doused'], sabotaged = row['Sabotaged'], marked = row['Marked'], revealed_mayor = row['Revealed Mayor'])] = []
                else:
                    self.player_dict[role_class(name = row['Name'], email = row['Email'], player_dict = self.player_dict, dead = True, actions_used = row['Actions used'], revealed_mayor = row['Revealed Mayor'])] = []
            else:
                print('Error in creating ' + row['Role'] + ' role')


    # There may be a more efficient way to do this
    def set_targets(self):
        for _, row in self.actions_df.iterrows():
            for player in self.player_dict:
                # Setting arsonist action choice
                if str(type(player).__name__) == 'Arsonist':
                    arsonist_action = row['Arsonist only: \'Douse\' \'Undouse\' or \'Ignite\'']
                    if arsonist_action == 'Undouse' or arsonist_action == 'Ignite':
                        player.arso_action = arsonist_action
                # Setting targets for all players
                for target in self.player_dict:
                    if player.get_name() == row['Name'] and target.get_name() == row['Who do you want to target with your night action']:
                        player.select_target(target)

        for _, row in self.actions_df.iterrows():
            for player in self.player_dict:
                for target in self.player_dict:
                    if player.get_name() == row['Name'] and target.get_name() == row['Who do you want your second target to be']:
                        player.select_target2(target)


    def run_actions(self):
        priority_list = ['Bus_driver', 'Limo_driver', 'Veteran', 'Witch', 'Escort', 'Hooker', 'Framer', 'Cop', 'Detective', 'Doctor', 'Bodyguard', 'Survivor', 'Vigilante', 'Godfather', 'Sniper', 'Mass_murderer', 'Serial_killer', 'Arsonist', 'Janitor', 'Tracker', 'Stalker', 'Watcher', 'Lookout', 'Saboteur', 'Amnesiac']
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
