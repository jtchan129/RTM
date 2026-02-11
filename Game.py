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

# Folder to hold game states and the role distribution csv files
DATA_DIR = os.path.join(os.path.dirname(__file__), "Game Data")
os.makedirs(DATA_DIR, exist_ok=True)

# Takes a Google Sheets file ID and a name for the .csv file the data will be saved to
# Taken and adapted from https://docs.gspread.org/en/latest/oauth2.html and https://docs.gspread.org/en/latest/user-guide.html#using-gspread-with-pandas
def pull_data(file_id, file_name):
    gc = gspread.service_account(filename=google_API_credentials_path)

    sheet = gc.open_by_key(file_id)
    worksheet = sheet.get_worksheet(0)

    dataframe = pd.DataFrame(worksheet.get_all_records())

    if file_name != None:
        dataframe.to_csv(file_name, index=False)

    return dataframe, worksheet

# Reupload the file to Google Drive
def update_file(dataframe, worksheet):
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

# Remove all data besides headers from a sheet
def clear_data(worksheet):
    worksheet.resize(rows=1)
    worksheet.resize(rows=150)

# Mode should be 'night'. 'day', 'newGF', or 'reveal', if mode = None then it will get the overall most recent state
def find_last_file(mode):
    if not os.path.isdir(DATA_DIR):
        files = []
    else:
        files = [f for f in os.listdir(DATA_DIR) if f.startswith('game_state') and f.endswith('.csv')]
    if not files:
        return 0, None, 0

    # Filtering by files of type {mode} if specified
    if mode:
        mode_files = [f for f in files if mode in f]
        if not mode_files:
            last_mode_num = 0
        else:
            last_mode_num = max([int(f.split(mode)[-1].split('.csv')[0]) for f in mode_files])
    else:
        last_mode_num = 0

    # Getting state numbers
    state_numbers = [int(f.split('state')[-1].split('_', 2)[0]) for f in files]
    last_state_num = max(state_numbers)
    last_state_file = files[state_numbers.index(last_state_num)]

    return last_state_num, last_state_file, last_mode_num

# Returns the number of state files in the DATA_DIR directory
def num_state_files():
    if not os.path.isdir(DATA_DIR):
        return 0
    else:
        files = [f for f in os.listdir(DATA_DIR) if f.startswith('game_state') and f.endswith('.csv')]
    
    return len(files)


# Adapted from https://stackoverflow.com/questions/10147455/how-to-send-an-email-with-gmail-as-provider-using-python/27515833#27515833 and https://mailtrap.io/blog/python-send-email/
def send_email(receiver_email, message_text_list, subject):
    message_text = ''
    for text in message_text_list:
        message_text = message_text + ' ' + text
    
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
        self.night_preview_df = None
        self.night_public_result_preview = None

    # ranodmize_roles, assign_roles, run_night, and run_voting are independent of each other: They are never run on the same game object they individually interact with the game_state.csv file
    def randomize_roles(self, role_dist_df):
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

        # Return the final df of role categories and actual roles
        return role_dist_df

    # CURRENTLY UNUSED IN STREAMLIT APP
    # Assign players roles based on the role distribution
    def assign_roles(self):
        state_df, state_worksheet = pull_data(players_link_id, os.path.join(DATA_DIR, 'game_state0_day0.csv'))
        role_dist_df, _ = pull_data(role_distribution_link_id, os.path.join(DATA_DIR, 'role_distribution.csv'))
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

        # # Saving roles in csv and Google Sheets
        # state_df.to_csv('game_state0_day0.csv', index=False)
        # update_file(state_df[['Name', 'Email', 'Role']], state_worksheet)

        # Update self.state_df for the streamllit
        self.state_df = state_df


    # Send emails informing people of their roles
    def email_roles(self):
        state_df, _ = pull_data(players_link_id, os.path.join(DATA_DIR, 'game_state0_day0.csv'))
        
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
        state_df.to_csv(os.path.join(DATA_DIR, 'game_state0_day0.csv'), index=False)


    # Preview emails informing people of their roles
    def email_roles_preview(self):
        state_df = pd.read_csv(os.path.join(DATA_DIR, 'game_state0_day0.csv'))
        
        revealed_mafia_list = ['Godfather', 'Lookout', 'Framer', 'Sniper', 'Yakuza', 'Janitor', 'Limo_driver', 'Hooker', 'Stalker', 'Sniper']

        email_data = []
        mafia_emails = []
        mafia_names = []

        # Each players role
        for _, row in state_df.iterrows():
            message = f"Your role is {row['Role']}"
            subject = "RTM Role Assignments"
            email_data.append({
                "Name": row["Name"],
                "Email": row["Email"],
                "Role": row["Role"],
                "Email Preview": message,
                "Email Subject": subject
            })

            if row["Role"] in revealed_mafia_list:
                mafia_emails.append(row["Email"])
                mafia_names.append(row["Name"])
                
        gf_sheet_link = f"https://docs.google.com/spreadsheets/d/{newGF_link_id}"

        mafia_message = (
            f"The mafia members are: {', '.join(mafia_names)}"
            f"\n\nThe new Godfather Google Sheet is: {gf_sheet_link}"
        )
        # Mafia group email
        email_data.append({
            "Name": "All Mafia Members",
            "Email": ", ".join(mafia_emails),
            "Role": "Mafia Coordination",
            "Email Preview": mafia_message,
            "Email Subject": "Mafia members"
        })

        return pd.DataFrame(email_data)


    def run_night(self, preview_only=True):
        # Find most recent game state number, game state number, and night number and set accordingly
        last_state_num, last_state_file, last_night_num = find_last_file('night')
        self.state_num = last_state_num + 1
        self.night_num =  last_night_num + 1

        # Load last game state file
        self.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))

        # Load file of night actions from google drive
        self.actions_df, actions_worksheet = pull_data(actions_link_id, os.path.join(DATA_DIR, 'actions_night' + str(self.night_num) + '.csv'))

        # Taking only the most recent action for each player
        self.actions_df['Timestamp'] = pd.to_datetime(self.actions_df['Timestamp'])
        self.actions_df = self.actions_df.sort_values(by='Timestamp').drop_duplicates(subset=['Name'], keep='last')
        self.actions_df.to_csv(os.path.join(DATA_DIR, f'actions_night{self.night_num}.csv'), index=False)

        # Creating set of play objects
        self.create_players()

        # Create the group email to send public results
        self.create_rtm_group_email()

        # Setting targets
        self.set_targets()

        # Run actions in priority order
        self.run_actions()

        # Process deaths
        self.process_deaths(preview_only)

        # Creating preview data
        email_data = []

        # Add public result row
        email_data.append({
            "Name": "Public",
            "Email": "Everyone",
            "Role": "Public Results",
            "Results Preview": [self.public_result]
        })

        for player in self.player_dict.keys():
            result_msg = player.get_results()
            email_data.append({
                "Name": player.get_name(),
                "Email": player.get_email(),
                "Role": type(player).__name__,
                "Results Preview": result_msg
            })

        preview_df = pd.DataFrame(email_data)

        # If preview_only, return preview and exit without modifying files or sending emails
        if preview_only:
            return preview_df

        # If not preview_only, send emails, clear actions, and update state file
        self.email_results()
        send_email(self.rtm_group_email, self.public_result, 'Night ' + str(self.night_num) + ' public results')
        clear_data(actions_worksheet)
        self.update_state_file()

        return None

    def run_voting(self, preview_only=True):
        # Find most recent game state number, game state file name, and day number and set accordingly
        last_state_num, last_state_file, last_day_num = find_last_file('day')
        self.state_num = last_state_num + 1
        day_num = last_day_num + 1

        day_column_name = 'Day ' + str(day_num)

        # Load the last game state file
        self.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))

        # Create the group email to send public results
        self.create_rtm_group_email()

        self.voting_df, voting_worksheet = pull_data(voting_link_id, os.path.join(DATA_DIR, 'voting_day' + str(day_num) + '.csv'))

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

        # Creating vote summary for preview
        vote_summary = {
            player: votes
            for player, votes in voting_dict.items()
            if votes > 0
        }

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
            if most_voted == 'No vote':
                self.public_result = 'On day ' + str(day_num) + ', the town of Pi voted to not execute anyone by a no vote'
            else:
                # Getting voted player's role
                most_voted_role = self.state_df.loc[self.state_df['Name'] == most_voted, 'Role'].values[0]
                self.public_result = 'On day ' + str(day_num) + ', the town of Pi voted to execute ' + most_voted + ' the ' + most_voted_role

                # Full execution for if not in preview mode
                if not preview_only:
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
        
        # Return the public result if in preview mode
        if preview_only:
            return self.public_result, vote_summary

        # Send the email and save the file if not in preview mode
        send_email(self.rtm_group_email, self.public_result, 'Day ' + str(day_num) + ' execution results')
        filename = f'game_state{self.state_num}_day{day_num}.csv'
        self.state_df.to_csv(os.path.join(DATA_DIR, filename), index=False)


    def assign_new_godfather(self):
        last_state_num, last_state_file, last_newGF_num = find_last_file('newGF')
        self.state_num = last_state_num + 1
        newGF_num = last_newGF_num + 1

        # Load the last game state file
        self.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))

        newGF_df, _ = pull_data(newGF_link_id, os.path.join(DATA_DIR, 'newGF' + str(newGF_num) + '.csv'))
        newGF_name = newGF_df.loc[0, 'New godfather']

        player_index = self.state_df[self.state_df['Name'] == newGF_name].index

        newGF_mafia_list = ['Mafioso', 'Limo_driver', 'Stalker', 'Lookout', 'Hooker', 'Janitor', 'Framer', 'Yakuza', 'Saboteur', 'Sniper']

        if self.state_df.loc[player_index, 'Role'].values[0] in newGF_mafia_list:
            self.state_df.loc[player_index, 'Role'] = 'Godfather'
            filename = f'game_state{self.state_num}_newGF{newGF_num}.csv'
            self.state_df.to_csv(os.path.join(DATA_DIR, filename), index=False)
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
        self.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))

        self.create_rtm_group_email()

        player_index = self.state_df[self.state_df['Name'] == mayor_name].index

        if len(player_index) == 0:
            print('Name not found')
            return

        if self.state_df.loc[player_index, 'Role'].values[0] == 'Mayor':
            self.state_df.loc[player_index, 'Revealed Mayor'] = 1
            
            send_email(self.rtm_group_email, mayor_name + ' has revealed themselves as mayor', 'Mayor reveal')
            filename = f'game_state{self.state_num}_reveal{reveal_num}.csv'
            self.state_df.to_csv(os.path.join(DATA_DIR, filename), index=False)
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


    def process_deaths(self, preview_only):
        self.public_result = 'In the town of Pi the villagers awoke after night ' + str(self.night_num)
        dead_list = []

        # Editing the state_df
        for player in self.player_dict:
            if player.died_tonight == True:
                if preview_only == False:
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

        filename = f'game_state{self.state_num}_night{self.night_num}.csv'
        self.state_df.to_csv(os.path.join(DATA_DIR, filename), index=False)

    # Not currently being used
    def check_win_conditions(self):
        last_state_num, last_state_file, last_night_num = find_last_file('night')
        self.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))

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