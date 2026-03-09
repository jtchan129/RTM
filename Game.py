import pandas as pd
import Roles
import gspread
from collections import defaultdict
import os
import random
import smtplib
from email.mime.text import MIMEText


# These are the fields that need to be changed before the start of a game
#####################################################################################################################
players_link_id = "1q-C1SNAMmPUx__y5gxaviZFv1e-BiMeUH9TQUxmvxmE"
role_distribution_link_id = "1tGCLbzXLsFyG4JRi0D2SRUeCFSLCN5IeUXZzHj-BCC4"
actions_link_id = "1qZfl1y6T73z_AKxu_1WhrR0Q1AgfvttBSzqOMVwvJiI"
voting_link_id = "1rdUudou9gnQO_P-dYSss-Sp8lCxWZPpLx-S-Bnko2UM"
newGF_link_id = "1eFGj0u9iAy7FBw0lMS96sdWwobCyrHaAZ21prVnbO88"

google_API_credentials_path = "real-time-mafia-175d61ce3729.json"
mod_email_app_password_path = "mod_email_app_password.csv"
#####################################################################################################################

# Folder to hold game states and the role distribution csv files
DATA_DIR = os.path.join(os.path.dirname(__file__), "Game Data")
os.makedirs(DATA_DIR, exist_ok=True)


def clean_string(value):
    if value is None or pd.isna(value):
        return ""
    text = str(value).replace("_", " ")
    return " ".join(text.strip().split()).lower()


# Takes a Google Sheets file ID and a name for the .csv file the data will be saved to
# Taken and adapted from https://docs.gspread.org/en/latest/oauth2.html and https://docs.gspread.org/en/latest/user-guide.html#using-gspread-with-pandas
def pull_data(file_id, file_name):
    gc = gspread.service_account(filename=google_API_credentials_path)

    sheet = gc.open_by_key(file_id)
    worksheet = sheet.get_worksheet(0)

    dataframe = pd.DataFrame(worksheet.get_all_records())

    if file_name is not None:
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
        files = [
            f
            for f in os.listdir(DATA_DIR)
            if f.startswith("game_state") and f.endswith(".csv")
        ]
    if not files:
        return 0, None, 0

    # Filtering by files of type {mode} if specified
    if mode:
        mode_files = [f for f in files if mode in f]
        if not mode_files:
            last_mode_num = 0
        else:
            last_mode_num = max(
                [int(f.split(mode)[-1].split(".csv")[0]) for f in mode_files]
            )
    else:
        last_mode_num = 0

    # Getting state numbers
    state_numbers = [int(f.split("state")[-1].split("_", 2)[0]) for f in files]
    last_state_num = max(state_numbers)
    last_state_file = files[state_numbers.index(last_state_num)]

    return last_state_num, last_state_file, last_mode_num


# Returns the number of state files in the DATA_DIR directory
def num_state_files():
    if not os.path.isdir(DATA_DIR):
        return 0
    else:
        files = [
            f
            for f in os.listdir(DATA_DIR)
            if f.startswith("game_state") and f.endswith(".csv")
        ]

    return len(files)


# Adapted from https://stackoverflow.com/questions/10147455/how-to-send-an-email-with-gmail-as-provider-using-python/27515833#27515833 and https://mailtrap.io/blog/python-send-email/
def send_email(receiver_email, message_text_list, subject):
    # Creating the body of the email
    if isinstance(message_text_list, list):
        message_text = " ".join(message_text_list)
    else:
        message_text = str(message_text_list)

    dataframe = pd.read_csv(mod_email_app_password_path)
    sender_email = dataframe.loc[0, "email"]
    sender_app_password = dataframe.loc[0, "app_password"]

    smtpserver = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    smtpserver.ehlo()
    smtpserver.login(sender_email, sender_app_password)

    # Create MIMEText object
    message = MIMEText(message_text, "plain")
    message["Subject"] = subject
    message["From"] = sender_email

    # Join emails if sending to mutiple
    if isinstance(receiver_email, str):
        message["To"] = receiver_email
    elif isinstance(receiver_email, list):
        message["To"] = ", ".join(receiver_email)

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
        self.public_result = ""
        self.night_preview_df = None
        self.night_public_result_preview = None

    # ranodmize_roles, assign_roles, run_night, and run_voting are independent of each other: They are never run on the same game object they individually interact with the game_state.csv file
    def randomize_roles(self, role_dist_df):
        # Randomly select role distribution based on categories
        town_investigative_list = ["Detective", "Cop", "Tracker", "Watcher"]
        town_killing_list = ["Vigilante", "Bodyguard", "Veteran", "Bomb"]
        town_support_list = ["Mayor", "Bus_driver", "Escort", "Doctor"]
        town_random_list = [
            "Detective",
            "Cop",
            "Tracker",
            "Watcher",
            "Vigilante",
            "Bodyguard",
            "Veteran",
            "Bomb",
            "Mayor",
            "Bus_driver",
            "Escort",
            "Doctor",
        ]
        mafia_list = [
            "Lookout",
            "Framer",
            "Sniper",
            "Yakuza",
            "Janitor",
            "Limo_driver",
            "Hooker",
            "Stalker",
            "Sniper",
            "Saboteur",
        ]
        neutral_list = [
            "Amnesiac",
            "Arsonist",
            "Jester",
            "Witch",
            "Serial_killer",
            "Survivor",
            "Mass_murderer",
        ]
        # Used to assign specific roles
        full_roles_list = [
            "Detective",
            "Cop",
            "Tracker",
            "Watcher",
            "Vigilante",
            "Bodyguard",
            "Veteran",
            "Bomb",
            "Mayor",
            "Bus_driver",
            "Escort",
            "Doctor",
            "Godfather",
            "Lookout",
            "Framer",
            "Sniper",
            "Yakuza",
            "Janitor",
            "Limo_driver",
            "Hooker",
            "Stalker",
            "Sniper",
            "Saboteur",
            "Amnesiac",
            "Arsonist",
            "Jester",
            "Witch",
            "Serial_killer",
            "Survivor",
            "Mass_murderer",
        ]
        # Used in removing unique roles
        role_lists_list = [
            town_investigative_list,
            town_killing_list,
            town_support_list,
            town_random_list,
            mafia_list,
            neutral_list,
            full_roles_list,
        ]
        full_roles_lookup = {clean_string(role): role for role in full_roles_list}

        # This can be expanded later to put limits on the number of each role in the game
        unique_dict = {
            "Bomb": 1,
            "Mayor": 1,
            "Bus_driver": 1,
            "Limo_driver": 1,
            "Sniper": 1,
            "Saboteur": 1,
            "Amnesiac": 1,
        }

        for index, row in role_dist_df.iterrows():
            category_key = clean_string(row["Role Distribution Category"])
            if category_key:
                assigned_role = ""
                if category_key == clean_string("Town Investigative"):
                    assigned_role = random.choice(town_investigative_list)
                elif category_key == clean_string("Town Killing"):
                    assigned_role = random.choice(town_killing_list)
                elif category_key == clean_string("Town Support"):
                    assigned_role = random.choice(town_support_list)
                elif category_key == clean_string("Town Random"):
                    assigned_role = random.choice(town_random_list)
                elif category_key == clean_string("Mafia"):
                    assigned_role = random.choice(mafia_list)
                elif category_key == clean_string("Neutral"):
                    assigned_role = random.choice(neutral_list)
                elif category_key in full_roles_lookup:
                    assigned_role = full_roles_lookup[category_key]
                else:
                    print("Error in generating roles")

                for unique_role in unique_dict:
                    if clean_string(assigned_role) == clean_string(unique_role):
                        unique_dict[unique_role] = unique_dict[unique_role] - 1
                    if unique_dict[unique_role] == 0:
                        for role_list in role_lists_list:
                            if unique_role in role_list:
                                role_list.remove(unique_role)

                role_dist_df.loc[index, "Actual Role Distribution"] = assigned_role

        # Return the final df of role categories and actual roles
        return role_dist_df

    # CURRENTLY UNUSED IN STREAMLIT APP
    # Assign players roles based on the role distribution
    def assign_roles(self):
        state_df, state_worksheet = pull_data(
            players_link_id, os.path.join(DATA_DIR, "game_state0_day0.csv")
        )
        role_dist_df, _ = pull_data(
            role_distribution_link_id, os.path.join(DATA_DIR, "role_distribution.csv")
        )
        role_assignments_list = role_dist_df["Actual Role Distribution"].tolist()

        state_df["Time died"] = "Alive"
        state_df["Actions used"] = 0
        state_df["Doused"] = 0
        state_df["Sabotaged"] = 0
        state_df["Marked"] = 0
        state_df["Revealed Mayor"] = 0

        # Populate the players roles randomly with the roles from the generated distribution
        random.shuffle(role_assignments_list)
        for index, row in state_df.iterrows():
            state_df.loc[index, "Role"] = role_assignments_list[index]

        # # Saving roles in csv and Google Sheets
        # state_df.to_csv('game_state0_day0.csv', index=False)
        # update_file(state_df[['Name', 'Email', 'Role']], state_worksheet)

        # Update self.state_df for the streamllit
        self.state_df = state_df

    # Send emails informing people of their roles
    def email_roles(self):
        state_df, _ = pull_data(
            players_link_id, os.path.join(DATA_DIR, "game_state0_day0.csv")
        )

        revealed_mafia_list = [
            "Godfather",
            "Lookout",
            "Framer",
            "Sniper",
            "Yakuza",
            "Janitor",
            "Limo_driver",
            "Hooker",
            "Stalker",
            "Sniper",
        ]
        mafia_emails = []
        mafia_message = ["The mafia members are"]
        for index, row in state_df.iterrows():
            email_message = "Your role is " + row["Role"]
            email_subject = "RTM Role Assignments"
            send_email(row["Email"], email_message, email_subject)
            if row["Role"] in revealed_mafia_list:
                mafia_emails.append(row["Email"])
                mafia_message.append(row["Name"])

        gf_sheet_link = f"https://docs.google.com/spreadsheets/d/{newGF_link_id}"
        mafia_message.append(f"\n\nThe new Godfather Google Sheet is: {gf_sheet_link}")
        mafia_subject = "Mafia members"
        send_email(mafia_emails, mafia_message, mafia_subject)

        state_df["Time died"] = "Alive"
        state_df["Actions used"] = 0
        state_df["Doused"] = 0
        state_df["Sabotaged"] = 0
        state_df["Marked"] = 0
        state_df["Revealed Mayor"] = 0

        # Saving roles to csv again in case they were manually changed in the Google sheet
        state_df.to_csv(os.path.join(DATA_DIR, "game_state0_day0.csv"), index=False)

    # Preview emails informing people of their roles
    def email_roles_preview(self):
        state_df = pd.read_csv(os.path.join(DATA_DIR, "game_state0_day0.csv"))

        revealed_mafia_list = [
            "Godfather",
            "Lookout",
            "Framer",
            "Sniper",
            "Yakuza",
            "Janitor",
            "Limo_driver",
            "Hooker",
            "Stalker",
            "Sniper",
        ]

        email_data = []
        mafia_emails = []
        mafia_names = []

        # Each players role
        for _, row in state_df.iterrows():
            message = f"Your role is {row['Role']}"
            subject = "RTM Role Assignments"
            email_data.append(
                {
                    "Name": row["Name"],
                    "Email": row["Email"],
                    "Role": row["Role"],
                    "Email Preview": message,
                    "Email Subject": subject,
                }
            )

            if row["Role"] in revealed_mafia_list:
                mafia_emails.append(row["Email"])
                mafia_names.append(row["Name"])

        gf_sheet_link = f"https://docs.google.com/spreadsheets/d/{newGF_link_id}"

        mafia_message = (
            f"The mafia members are: {', '.join(mafia_names)}"
            f"\n\nThe new Godfather Google Sheet is: {gf_sheet_link}"
        )
        # Mafia group email
        email_data.append(
            {
                "Name": "All Mafia Members",
                "Email": ", ".join(mafia_emails),
                "Role": "Mafia Coordination",
                "Email Preview": mafia_message,
                "Email Subject": "Mafia members",
            }
        )

        return pd.DataFrame(email_data)

    def run_night(self, preview_only=True, custom_public_result=None):
        # Find most recent game state number, game state number, and night number and set accordingly
        last_state_num, last_state_file, last_night_num = find_last_file("night")
        self.state_num = last_state_num + 1
        self.night_num = last_night_num + 1

        # Load last game state file
        self.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))

        # Load file of night actions from google drive
        self.actions_df, actions_worksheet = pull_data(
            actions_link_id,
            os.path.join(DATA_DIR, "actions_night" + str(self.night_num) + ".csv"),
        )

        # Taking only the most recent action for each player
        self.actions_df["Timestamp"] = pd.to_datetime(self.actions_df["Timestamp"])
        self.actions_df["Name_clean"] = self.actions_df["Name"].apply(clean_string)
        self.actions_df = self.actions_df.sort_values(by="Timestamp").drop_duplicates(
            subset=["Name_clean"], keep="last"
        )
        self.actions_df = self.actions_df.drop(columns=["Name_clean"])
        self.actions_df.to_csv(
            os.path.join(DATA_DIR, f"actions_night{self.night_num}.csv"), index=False
        )

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

        # Checking for amnesiac remembering to add to public result
        for player in self.player_dict:
            if str(type(player).__name__) == "Amnesiac":
                if player.remembered_role != "Amnesiac":
                    self.public_result = (
                        self.public_result
                        + " An amnesiac remembered they were a "
                        + player.remembered_role
                        + "."
                    )

        # Creating preview data
        email_data = []

        # Add public result row
        email_data.append(
            {
                "Name": "Public",
                "Email": "Everyone",
                "Role": "Public Results",
                "Results Preview": [self.public_result],
            }
        )

        for player in self.player_dict.keys():
            result_msg = player.get_results()
            email_data.append(
                {
                    "Name": player.get_name(),
                    "Email": player.get_email(),
                    "Role": type(player).__name__,
                    "Results Preview": result_msg,
                }
            )

        preview_df = pd.DataFrame(email_data)

        # If preview_only, return preview and exit without modifying files or sending emails
        if preview_only:
            return preview_df

        # Send public email with default or custom public results if not in preview mode
        if custom_public_result is None:
            final_public_result = self.public_result
        else:
            final_public_result = custom_public_result
        send_email(
            self.rtm_group_email,
            final_public_result,
            "Night " + str(self.night_num) + " public results",
        )
        # If not preview_only, send emails, clear actions, and update state file
        self.email_results()
        clear_data(actions_worksheet)
        self.update_state_file()

        return None

    def run_voting(self, preview_only=True, custom_public_result=None):
        # Find most recent game state number, game state file name, and day number and set accordingly
        last_state_num, last_state_file, last_day_num = find_last_file("day")
        self.state_num = last_state_num + 1
        day_num = last_day_num + 1

        day_column_name = "Day " + str(day_num)

        # Load the last game state file
        self.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))

        # Create the group email to send public results
        self.create_rtm_group_email()

        self.voting_df, voting_worksheet = pull_data(
            voting_link_id, os.path.join(DATA_DIR, "voting_day" + str(day_num) + ".csv")
        )

        self.voting_df = self.voting_df[["Voting Player", day_column_name]]

        # Normalize names/statuses so votes are resilient to spacing and capitalization differences.
        self.state_df["_name_clean"] = self.state_df["Name"].apply(clean_string)
        self.state_df["_time_died_clean"] = self.state_df["Time died"].apply(
            clean_string
        )
        alive_state_df = self.state_df[
            self.state_df["_time_died_clean"] == clean_string("Alive")
        ]
        alive_name_lookup = {
            clean_string(name): name
            for name in alive_state_df["Name"].tolist()
            if clean_string(name)
        }
        alive_clean_names = set(alive_name_lookup.keys())

        voting_player_clean_col = "Voting Player clean"
        day_clean_col = day_column_name + " clean"
        voting_player_canonical_col = "Voting Player canonical"
        day_canonical_col = day_column_name + " canonical"
        no_vote_key = clean_string("No vote")

        self.voting_df[voting_player_clean_col] = self.voting_df["Voting Player"].apply(
            clean_string
        )
        self.voting_df[day_clean_col] = self.voting_df[day_column_name].apply(
            clean_string
        )
        self.voting_df[voting_player_canonical_col] = ""
        self.voting_df[day_canonical_col] = ""

        # Set any non-valid votes to blank
        for index, row in self.voting_df.iterrows():
            voting_player_alive = row[voting_player_clean_col] in alive_clean_names
            target_player_alive = (row[day_clean_col] in alive_clean_names) or (
                row[day_clean_col] == no_vote_key
            )

            if not voting_player_alive or not target_player_alive:
                self.voting_df.loc[index, day_column_name] = ""
            else:
                self.voting_df.loc[index, voting_player_canonical_col] = (
                    alive_name_lookup[row[voting_player_clean_col]]
                )
                if row[day_clean_col] == no_vote_key:
                    self.voting_df.loc[index, day_canonical_col] = "No vote"
                else:
                    self.voting_df.loc[index, day_canonical_col] = alive_name_lookup[
                        row[day_clean_col]
                    ]

        valid_votes_df = self.voting_df[self.voting_df[day_column_name] != ""][
            [voting_player_canonical_col, day_canonical_col]
        ]

        # Creating a dictionary to count votes
        voting_keys = list(self.state_df["Name"])
        voting_dict = {key: 0 for key in voting_keys}
        voting_dict["No vote"] = 0

        for _, row in valid_votes_df.iterrows():
            voter_mask = self.state_df["_name_clean"] == clean_string(
                row[voting_player_canonical_col]
            )
            is_revealed_mayor = (
                not self.state_df.loc[voter_mask, "Revealed Mayor"].empty
            ) and (self.state_df.loc[voter_mask, "Revealed Mayor"].values[0] == 1)

            if is_revealed_mayor:
                voting_dict[row[day_canonical_col]] = (
                    voting_dict[row[day_canonical_col]] + 3
                )
            else:
                voting_dict[row[day_canonical_col]] = (
                    voting_dict[row[day_canonical_col]] + 1
                )

        # Take the counts of votes and sort them to later find the maximum
        vote_counts = list(voting_dict.values())
        vote_counts.sort(reverse=True)

        # Creating vote summary for preview
        vote_summary = {
            player: votes for player, votes in voting_dict.items() if votes > 0
        }

        # Determining execute and public message
        if vote_counts[0] == 0:
            self.public_result = (
                "On day "
                + str(day_num)
                + ", the town of Pi voted to not execute anyone by a no vote"
            )
        elif vote_counts[0] == vote_counts[1]:
            self.public_result = (
                "On day "
                + str(day_num)
                + ", the town of Pi voted to not execute anyone by tied vote"
            )
        else:
            most_voted = None
            for voted_player, num_votes in voting_dict.items():
                if num_votes == vote_counts[0]:
                    most_voted = voted_player
            if most_voted == "No vote":
                self.public_result = (
                    "On day "
                    + str(day_num)
                    + ", the town of Pi voted to not execute anyone by a no vote"
                )
            else:
                # Getting voted player's role
                most_voted_role = self.state_df.loc[
                    self.state_df["_name_clean"] == clean_string(most_voted), "Role"
                ].values[0]
                self.public_result = (
                    "On day "
                    + str(day_num)
                    + ", the town of Pi voted to execute "
                    + most_voted
                    + " the "
                    + most_voted_role
                )

                # Full execution for if not in preview mode
                if not preview_only:
                    player_index = self.state_df[
                        self.state_df["_name_clean"] == clean_string(most_voted)
                    ].index
                    self.state_df.loc[player_index, "Time died"] = "Day " + str(day_num)

                    # Checking for Jester or Saboteur deaths
                    if self.state_df.loc[player_index, "Role"].values[0] == "Saboteur":
                        self.state_df.loc[self.state_df["Sabotaged"] == 1, "Marked"] = 1

                    if self.state_df.loc[player_index, "Role"].values[0] == "Jester":
                        jester_name = self.state_df.loc[player_index, "Name"].values[0]
                        vote_list = valid_votes_df[
                            (valid_votes_df[day_canonical_col] == most_voted)
                            & (
                                valid_votes_df[voting_player_canonical_col].apply(
                                    lambda value: (
                                        clean_string(value) != clean_string(jester_name)
                                    )
                                )
                            )
                        ][voting_player_canonical_col].tolist()
                        if vote_list:
                            jester_target_name = random.choice(vote_list)
                            jester_target_index = self.state_df[
                                self.state_df["_name_clean"]
                                == clean_string(jester_target_name)
                            ].index
                            self.state_df.loc[jester_target_index, "Marked"] = 1

        # Return the public result if in preview mode
        if preview_only:
            self.state_df = self.state_df.drop(
                columns=["_name_clean", "_time_died_clean"], errors="ignore"
            )
            return self.public_result, vote_summary

        # Send public email with default or custom public results if not in preview mode
        if custom_public_result is None:
            final_public_result = self.public_result
        else:
            final_public_result = custom_public_result
        send_email(
            self.rtm_group_email,
            final_public_result,
            "Day " + str(day_num) + " execution results",
        )
        # Save the file if not in preview mode
        self.state_df = self.state_df.drop(
            columns=["_name_clean", "_time_died_clean"], errors="ignore"
        )
        filename = f"game_state{self.state_num}_day{day_num}.csv"
        self.state_df.to_csv(os.path.join(DATA_DIR, filename), index=False)

    def assign_new_godfather(self):
        last_state_num, last_state_file, last_newGF_num = find_last_file("newGF")
        self.state_num = last_state_num + 1
        newGF_num = last_newGF_num + 1

        # Load the last game state file
        self.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))

        newGF_df, _ = pull_data(
            newGF_link_id, os.path.join(DATA_DIR, "newGF" + str(newGF_num) + ".csv")
        )
        newGF_name = newGF_df.loc[0, "New godfather"]
        newGF_name_clean = clean_string(newGF_name)

        player_index = self.state_df[
            self.state_df["Name"].apply(
                lambda value: clean_string(value) == newGF_name_clean
            )
        ].index
        if len(player_index) == 0:
            print("Name not found")
            return

        newGF_mafia_list = [
            "Mafioso",
            "Limo_driver",
            "Stalker",
            "Lookout",
            "Hooker",
            "Janitor",
            "Framer",
            "Yakuza",
            "Saboteur",
            "Sniper",
        ]
        newGF_mafia_set = {clean_string(role) for role in newGF_mafia_list}

        if (
            clean_string(self.state_df.loc[player_index, "Role"].values[0])
            in newGF_mafia_set
        ):
            self.state_df.loc[player_index, "Role"] = "Godfather"
            filename = f"game_state{self.state_num}_newGF{newGF_num}.csv"
            self.state_df.to_csv(os.path.join(DATA_DIR, filename), index=False)
            # Sending email
            newGF_email = self.state_df.loc[player_index[0], "Email"]
            subject = "You Are the New Godfather"
            message_text_list = ["You have been chosen as the new Godfather."]
            send_email(newGF_email, message_text_list, subject)

    def reveal_mayor(self, mayor_name):
        last_state_num, last_state_file, last_reveal_num = find_last_file("reveal")
        self.state_num = last_state_num + 1
        reveal_num = last_reveal_num + 1

        # Load the last game state file
        self.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))
        mayor_name_clean = clean_string(mayor_name)

        self.create_rtm_group_email()

        player_index = self.state_df[
            self.state_df["Name"].apply(
                lambda value: clean_string(value) == mayor_name_clean
            )
        ].index

        if len(player_index) == 0:
            print("Name not found")
            return

        if clean_string(
            self.state_df.loc[player_index, "Role"].values[0]
        ) == clean_string("Mayor"):
            self.state_df.loc[player_index, "Revealed Mayor"] = 1
            mayor_display_name = self.state_df.loc[player_index[0], "Name"]

            send_email(
                self.rtm_group_email,
                mayor_display_name + " has revealed themselves as mayor",
                "Mayor reveal",
            )
            filename = f"game_state{self.state_num}_reveal{reveal_num}.csv"
            self.state_df.to_csv(os.path.join(DATA_DIR, filename), index=False)
        else:
            print("Player is not a mayor")

    def create_rtm_group_email(self):
        for _, row in self.state_df.iterrows():
            email = row["Email"]
            if email:
                self.rtm_group_email.append(email)
            else:
                print("Error in adding email")

    def create_players(self):
        self.player_dict = defaultdict(list)
        role_lookup = {
            clean_string(role_name): role_class
            for role_name, role_class in vars(Roles).items()
            if isinstance(role_class, type)
        }

        for _, row in self.state_df.iterrows():
            role_class = role_lookup.get(clean_string(row["Role"]))
            if role_class:
                if clean_string(row["Time died"]) == clean_string("Alive"):
                    self.player_dict[
                        role_class(
                            name=row["Name"],
                            email=row["Email"],
                            player_dict=self.player_dict,
                            dead=False,
                            actions_used=row["Actions used"],
                            doused=row["Doused"],
                            sabotaged=row["Sabotaged"],
                            marked=row["Marked"],
                            revealed_mayor=row["Revealed Mayor"],
                        )
                    ] = []
                else:
                    self.player_dict[
                        role_class(
                            name=row["Name"],
                            email=row["Email"],
                            player_dict=self.player_dict,
                            dead=True,
                            actions_used=row["Actions used"],
                            revealed_mayor=row["Revealed Mayor"],
                        )
                    ] = []
            else:
                print("Error in creating " + row["Role"] + " role")

    # There may be a more efficient way to do this
    def set_targets(self):
        player_lookup = {
            clean_string(player.get_name()): player
            for player in self.player_dict
            if clean_string(player.get_name())
        }

        for _, row in self.actions_df.iterrows():
            player = player_lookup.get(clean_string(row["Name"]))
            if player is None:
                continue

            # Setting arsonist action choice
            if str(type(player).__name__) == "Arsonist":
                arsonist_action_clean = clean_string(
                    row["Arsonist only: 'Douse' 'Undouse' or 'Ignite'"]
                )
                if arsonist_action_clean == clean_string("Undouse"):
                    player.arso_action = "Undouse"
                elif arsonist_action_clean == clean_string("Ignite"):
                    player.arso_action = "Ignite"

            # Setting first target
            target = player_lookup.get(
                clean_string(row["Who do you want to target with your night action"])
            )
            if target is not None:
                player.select_target(target)

        for _, row in self.actions_df.iterrows():
            player = player_lookup.get(clean_string(row["Name"]))
            target2 = player_lookup.get(
                clean_string(row["Who do you want your second target to be"])
            )
            if player is not None and target2 is not None:
                player.select_target2(target2)

    def run_actions(self):
        priority_list = [
            "Veteran",
            "Bus_driver",
            "Limo_driver",
            "Witch",
            "Escort",
            "Hooker",
            "Framer",
            "Cop",
            "Detective",
            "Doctor",
            "Bodyguard",
            "Survivor",
            "Vigilante",
            "Godfather",
            "Sniper",
            "Mass_murderer",
            "Serial_killer",
            "Arsonist",
            "Janitor",
            "Tracker",
            "Stalker",
            "Watcher",
            "Lookout",
            "Saboteur",
            "Amnesiac",
        ]
        end_priotity_list = ["Janitor", "Bodyguard", "Bomb", "Doctor", "Yakuza"]

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
            if not player.dead and player.get_results():
                send_email(
                    player.get_email(),
                    player.get_results(),
                    "Night " + str(self.night_num) + " individual results",
                )

    def process_deaths(self, preview_only):
        self.public_result = "In the town of Pi the villagers awoke after night " + str(
            self.night_num
        )
        dead_list = []

        # Editing the state_df
        for player in self.player_dict:
            if player.died_tonight:
                if not preview_only:
                    player_index = self.state_df[
                        self.state_df["Name"].apply(
                            lambda value: (
                                clean_string(value) == clean_string(player.get_name())
                            )
                        )
                    ].index
                    self.state_df.loc[player_index, "Time died"] = "Night " + str(
                        self.night_num
                    )
                dead_list.append(player)

        # Preparing the public result
        if dead_list:
            self.public_result = self.public_result + " and found "
            for i in range(len(dead_list)):
                if dead_list[i].cleaned:
                    self.public_result = (
                        self.public_result
                        + dead_list[i].get_name()
                        + " the unknown (cleaned by janitor)"
                    )
                elif str(type(dead_list[i]).__name__) == "Yakuza":
                    self.public_result = (
                        self.public_result
                        + dead_list[i].get_name()
                        + " the "
                        + dead_list[i].revealed_role
                    )
                else:
                    self.public_result = (
                        self.public_result
                        + dead_list[i].get_name()
                        + " the "
                        + str(type(dead_list[i]).__name__)
                    )
                if i != len(dead_list) - 1:
                    self.public_result = self.public_result + " and "
                else:
                    self.public_result = self.public_result + " dead."

        else:
            self.public_result = self.public_result + " to a peaceful morning."

    # Update the file to include the number of actions each player has used, if they are doused or not, and reset the sabogated player
    def update_state_file(self):
        for player in self.player_dict:
            player_index = self.state_df[
                self.state_df["Name"].apply(
                    lambda value: clean_string(value) == clean_string(player.get_name())
                )
            ].index
            self.state_df.loc[player_index, "Actions used"] = player.actions_used
            self.state_df.loc[player_index, "Doused"] = player.doused
            self.state_df.loc[player_index, "Sabotaged"] = player.sabotaged
            self.state_df.loc[player_index, "Marked"] = 0

            # Checking for yakuza corruption
            if player.corrupted:
                self.state_df.loc[player_index, "Role"] = "Mafioso"

            # Checking for amnesiac remembering
            if str(type(player).__name__) == "Amnesiac":
                if player.remembered_role != "Amnesiac":
                    self.state_df.loc[player_index, "Role"] = player.remembered_role
                    self.state_df.loc[player_index, "Actions used"] = 0

        filename = f"game_state{self.state_num}_night{self.night_num}.csv"
        self.state_df.to_csv(os.path.join(DATA_DIR, filename), index=False)

    # Not currently being used
    def check_win_conditions(self):
        last_state_num, last_state_file, last_night_num = find_last_file("night")
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
        win_public_message = ""

        for player in self.player_dict:
            if player.faction == "Town":
                town_name_list.append(str(type(player).__name__))
                if not player.dead:
                    num_town += 1
            elif player.faction == "Mafia":
                mafia_name_list.append(str(type(player).__name__))
                if not player.dead:
                    num_mafia += 1
            elif player.faction == "Lethal neutral" and not player.dead:
                num_lethal_neutral += 1
                neutral_name_list.append(str(type(player).__name__))
            elif str(type(player).__name__) == "Survivor" and not player.dead:
                survivor_name_list.append(str(type(player).__name__))
            elif str(type(player).__name__) == "Witch" and not player.dead:
                witch_name_list.append(str(type(player).__name__))

        if num_mafia == 0 and num_lethal_neutral == 0 and num_town > 0:
            win_public_message = win_public_message + "Town wins!"
            winner_list = town_name_list
        if num_mafia > num_town and num_lethal_neutral == 0 and num_mafia > 0:
            win_public_message = win_public_message + "Mafia wins!"
            winner_list = mafia_name_list
        if num_mafia == 0 and num_town == 0 and num_lethal_neutral > 0:
            win_public_message = win_public_message + "Neutral lethals win!"
            winner_list = neutral_name_list
            for witch_name in witch_name_list:
                winner_list.append(witch_name)

        for survivor_name in survivor_name_list:
            winner_list.append(survivor_name)

        win_public_message = win_public_message + " Winners are: "
        for i in range(len(winner_list)):
            if i != len(winner_list) - 1:
                win_public_message = win_public_message + winner_list[i] + ", "
            else:
                win_public_message = win_public_message + "and " + winner_list[i]
