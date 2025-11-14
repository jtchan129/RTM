import streamlit as st
import glob
import os
from Game import *

# Folder to hold game states and the role distribution csv files
DATA_DIR = os.path.join(os.path.dirname(__file__), "Game Data")
os.makedirs(DATA_DIR, exist_ok=True)

st.set_page_config(page_title='Mafia Moderator Panel', layout='wide')
st.title('Mafia Moderator Panel')

# Find last state number and file and create the game
last_state_num, last_state_file, _ = find_last_file(None)
if 'game' not in st.session_state:
    game = Game()
    # Load most recent state
    if last_state_file:
        game.state_df = pd.read_csv(os.path.join(DATA_DIR, last_state_file))
        game.create_players()
    st.session_state['game'] = game

game = st.session_state['game']


page = st.sidebar.radio('Go to', [
    'Overview',
    'Role Distribution',
    'Role Assignment',
    'Email Roles',
    'Run Night Actions',
    'Voting Phase',
    'Utilities',
    'View Files'
])

# PAGE: Overview
if page == 'Overview':
    # Tools section
    st.subheader("Tools")

    # Restart game button and confimation
    if "confirm_restart" not in st.session_state:
        st.session_state["confirm_restart"] = False
    if "cancel_message" not in st.session_state:
        st.session_state["cancel_message"] = False
    if "restart_done" not in st.session_state:
        st.session_state["restart_done"] = False

    # Functions called by buttons
    def show_confirm():
        st.session_state["confirm_restart"] = True
        st.session_state["cancel_message"] = False
        st.session_state["restart_done"] = False

    def cancel_restart():
        st.session_state["confirm_restart"] = False
        st.session_state["cancel_message"] = True
        st.session_state["restart_done"] = False

    def confirm_restart():
        csv_files = glob.glob(os.path.join(DATA_DIR, "game_state*.csv"))
        for f in csv_files:
            os.remove(f)
        if 'game' in st.session_state:
            del st.session_state['game']
        st.session_state["confirm_restart"] = False
        st.session_state["cancel_message"] = False
        st.session_state["restart_done"] = True

    # Button logic
    if st.session_state["restart_done"]:
        st.success("Game successfully restarted!")
        st.session_state["restart_done"] = False

    elif st.session_state["confirm_restart"]:
        st.warning("Are you sure you want to restart the game? This cannot be undone.")
        cols = st.columns([1, 1])
        with cols[0]:
            st.button("Yes, Restart Game", on_click=confirm_restart)
        with cols[1]:
            st.button("Cancel", on_click=cancel_restart)

    else:
        if st.session_state["cancel_message"]:
            st.info("Restart cancelled.")
            st.session_state["cancel_message"] = False

        st.button("Restart Game", on_click=show_confirm)

    # Overview section
    st.header('Overview')

    if getattr(game, "state_df", None) is None or game.state_df.empty:
        game.state_df = pd.DataFrame(columns=[
            "Name",
            "Email",
            "Role",
            "Time died",
            "Actions used",
            "Doused",
            "Sabotaged",
            "Marked",
            "Revealed Mayor"
        ])
        st.warning("No game state found. Please randomize and assign roles first.")
    else:
        # Checkbox to show hidden columns
        hidden_col_button = st.checkbox('Show Hidden Columns', value=False)
        visible_cols = ['Name', 'Email', 'Time died']
        if hidden_col_button:
            visible_cols += ['Role', 'Actions used', 'Doused', 'Sabotaged', 'Marked', 'Revealed Mayor']

        # Checkbox to filter only living players
        filter_button = st.checkbox('Filter Dead Players', value=False)
        
        # Apply both filters together
        df_to_show = game.state_df.copy()
        if filter_button:
            df_to_show = df_to_show[df_to_show['Time died'] == 'Alive']
        
        # Show dataframe
        st.dataframe(df_to_show[visible_cols])


# PAGE: Role Distribution
if page == 'Role Distribution':
    if last_state_num >= 0:
        st.warning("The game state file has already been populated, role Distribution cannot be changed. Restart game to change distribution")
    else:
        if 'rand_key' not in st.session_state:
            st.session_state['rand_key'] = 0
        # Role lists for manual editing
        town_investigative_list = ['Detective', 'Cop', 'Tracker', 'Watcher']
        town_killing_list = ['Vigilante', 'Bodyguard', 'Veteran', 'Bomb']
        town_support_list = ['Mayor', 'Bus_driver', 'Escort', 'Doctor']
        town_random_list = ['Detective', 'Cop', 'Tracker', 'Watcher', 'Vigilante', 'Bodyguard', 'Veteran', 'Bomb', 'Mayor', 'Bus_driver', 'Escort', 'Doctor']
        mafia_list = ['Lookout', 'Framer', 'Sniper', 'Yakuza', 'Janitor', 'Limo_driver', 'Hooker', 'Stalker', 'Sniper', 'Saboteur']
        neutral_list = ['Amnesiac', 'Arsonist', 'Jester', 'Witch', 'Serial_killer', 'Survivor', 'Mass_murderer']
        full_roles_list = ['Detective', 'Cop', 'Tracker', 'Watcher', 'Vigilante', 'Bodyguard', 'Veteran', 'Bomb', 'Mayor', 'Bus_driver', 'Escort', 'Doctor', 'Godfather', 'Lookout', 'Framer', 'Sniper', 'Yakuza', 'Janitor', 'Limo_driver', 'Hooker', 'Stalker', 'Sniper', 'Saboteur', 'Amnesiac', 'Arsonist', 'Jester', 'Witch', 'Serial_killer', 'Survivor', 'Mass_murderer']
        unique_dict = {'Bomb': 1,
                        'Mayor': 1,
                        'Bus_driver': 1,
                        'Limo_driver': 1,
                        'Sniper': 1,
                        'Saboteur': 1,
                        "Amnesiac": 1}
        required_dict = {'Godfather': 1}

        st.header('Role Distribution')
        # Pulling data from the Google Sheet
        if 'role_dist_df' not in st.session_state:
            st.session_state['role_dist_df'], st.session_state['role_dist_worksheet'] = pull_data(role_distribution_link_id, os.path.join(DATA_DIR, 'role_distribution.csv'))

        # Category options
        category_options = ['Town Investigative', 'Town Killing', 'Town Support', 'Town Random', 'Mafia', 'Neutral'] + full_roles_list

        # Random role distribution
        if st.button('Randomize Role Distribution'):
            st.session_state['role_dist_df'] = game.randomize_roles(st.session_state['role_dist_df'])
            st.session_state['rand_key'] += 1
            st.success('Roles have been randomized!')
        
        role_dist_df = st.session_state['role_dist_df']

        # Manual role distribution
        header_cols = st.columns([1, 1])
        header_cols[0].markdown("**Role Distribution Category**")
        header_cols[1].markdown("**Actual Role Distribution**")

        # Track changes
        updated_roles = []
        
        # Render table row by row
        for i, row in role_dist_df.iterrows():
            cols = st.columns([1, 1])
            category = row['Role Distribution Category']
            current_role = row['Actual Role Distribution']

            # Category column
            new_cat = cols[0].selectbox(
                label=f"Category",
                options=category_options,
                index=category_options.index(category),
                key=f"cat_{i}_{st.session_state['rand_key']}",
                label_visibility="collapsed"
            )

            if new_cat in full_roles_list:
                role_options = [new_cat]
            elif new_cat == 'Town Investigative':
                role_options = town_investigative_list
            elif new_cat == 'Town Killing':
                role_options = town_killing_list
            elif new_cat == 'Town Support':
                role_options = town_support_list
            elif new_cat == 'Town Random':
                role_options = town_random_list
            elif new_cat == 'Mafia':
                role_options = mafia_list
            elif new_cat == 'Neutral':
                role_options = neutral_list
            else:
                role_options = town_random_list + mafia_list + neutral_list

            # Actual role column
            new_role = cols[1].selectbox(
                label=f"Select for {new_cat}",
                options=role_options,
                index=role_options.index(current_role) if current_role in role_options else 0,
                key=f"role_{i}_{st.session_state['rand_key']}",
                label_visibility="collapsed"
            )

            updated_roles.append({
                'Role Distribution Category': new_cat,
                'Actual Role Distribution': new_role
            })

        updated_df = pd.DataFrame(updated_roles)

        # Checking if any roles that do not meet their requirements
        violations = []
        for role, limit in unique_dict.items():
            count = (updated_df['Actual Role Distribution'] == role).sum()
            if count > limit:
                violations.append(f"'{role}' appears {count} times (limit {limit})")
        for role, minimum in required_dict.items():
            count = (updated_df['Actual Role Distribution'] == role).sum()
            if count < minimum:
                violations.append(f"'{role}' appears {count} times (minimum {minimum})")

        if violations:
            st.warning("Some roles violate their requirements:\n" + "\n".join(violations))
            save_disabled = True
        else:
            save_disabled = False

        # Saving the role distribution
        if st.button('Save Role Distribution Changes', disabled=save_disabled):
            updated_df.to_csv(os.path.join(DATA_DIR, 'role_distribution.csv'), index=False)
            update_file(updated_df, st.session_state['role_dist_worksheet'])
            st.session_state['role_dist_df'] = updated_df
            st.success("Role Distribution saved!")


# PAGE: Role Assignment
elif page == 'Role Assignment':
    if last_state_num > 0:
        st.warning("The game has already started. Role Assignments cannot be changed.")
    else:
        # Getting the initial player data from the Role Assignments worksheet
        if getattr(game, "state_df", None) is None or game.state_df.empty:
            game.state_df, state_worksheet = pull_data(players_link_id, None)
            game.state_df['Time died'] = 'Alive'
            game.state_df['Actions used'] = 0
            game.state_df['Doused'] = 0
            game.state_df['Sabotaged'] = 0
            game.state_df['Marked'] = 0
            game.state_df['Revealed Mayor'] = 0
        else:
            __, state_worksheet = pull_data(players_link_id, None)
        
        role_dist_df = pd.read_csv(os.path.join(DATA_DIR, 'role_distribution.csv'))
        roles = role_dist_df['Actual Role Distribution'].tolist()
        prev_roles = st.session_state.get('prev_roles', [])
        all_players = game.state_df['Name'].tolist()
        
        st.header('Role Assignment')
        st.write('Use this section to randomly or manually assign player roles before starting the game.')

        # Initializing variables
        if 'player_rand_key' not in st.session_state:
            st.session_state['player_rand_key'] = 0

        # If role distribution changed, refresh assignments
        if roles != prev_roles or 'randomized_assignments' not in st.session_state:
            shuffled_players = all_players.copy()
            random.shuffle(shuffled_players)
            st.session_state['randomized_assignments'] = [{"Role": r, "Name": shuffled_players[i % len(shuffled_players)]} for i, r in enumerate(roles)]
            st.session_state['prev_roles'] = roles

        # Random assignment
        if st.button('Assign Roles Randomly'):
            shuffled_players = all_players.copy()
            random.shuffle(shuffled_players)
            randomized_assignments = [{"Role": r, "Name": p} for r, p in zip(roles, shuffled_players)]
            st.session_state['randomized_assignments'] = randomized_assignments
            st.session_state['player_rand_key'] += 1
            st.success('Roles randomly assigned to players')

        assignments = st.session_state['randomized_assignments']

        updated_assignments = []

        # Create visual table
        st.subheader("Assign Players to Roles")
        header_cols = st.columns([1, 1])
        header_cols[0].markdown("**Role**")
        header_cols[1].markdown("**Player**")
        for i, assign in enumerate(assignments):
            cols = st.columns([1, 1])
            cols[0].write(assign["Role"])
            selected_player = cols[1].selectbox(
                label=f"Select player for {assign['Role']}",
                options=all_players,
                index=all_players.index(assign["Name"]),
                key=f"player_select_{i}_{st.session_state['player_rand_key']}",
                label_visibility="collapsed"
            )
            updated_assignments.append({"Role": assign["Role"], "Name": selected_player})

        updated_df = pd.DataFrame(updated_assignments)

        # Checking for duplicates
        player_counts = updated_df['Name'].value_counts()
        duplicate_players = player_counts[player_counts > 1].index.tolist()
        unassigned_players = [p for p in all_players if p not in updated_df['Name'].tolist()]

        if duplicate_players or unassigned_players:
            if duplicate_players:
                st.warning(f"The following players have multiple roles: {', '.join(duplicate_players)}")
            if unassigned_players:
                st.warning(f"The following players have no role assigned: {', '.join(unassigned_players)}")
            save_disabled = True
        else:
            save_disabled = False

        # Saving the role assignments
        if st.button("Save Role Assignments", disabled=save_disabled):
            st.success("Role assignments updated!")
            for _, row in updated_df.iterrows():
                role = row['Role']
                name = row['Name']
                game.state_df.loc[game.state_df['Name'] == name, 'Role'] = role
            # Saving roles in csv and Google Sheets
            game.state_df.to_csv(os.path.join(DATA_DIR, 'game_state0_day0.csv'), index=False)
            update_file(game.state_df[['Name', 'Email', 'Role']], state_worksheet)


# PAGE: Email Roles
elif page == 'Email Roles':
    st.header('Email Roles to Players')
    st.write('Preview and send each player an email with their assigned role.')
    # Preview email button
    if st.button('Preview Emails'):
        st.session_state['email_df'] = game.email_roles_preview()

    # Send email button
    if 'email_df' in st.session_state and not st.session_state['email_df'].empty:
        email_df = st.session_state['email_df']
        st.dataframe(email_df)

        if st.button('Send Emails'):
            for _, row in email_df.iterrows():
                # Parsing emails
                receiver_field = row['Email']
                if isinstance(receiver_field, str) and ',' in receiver_field:
                    receiver_email = [e.strip() for e in receiver_field.split(',')]
                else:
                    receiver_email = receiver_field
                message_text_list = [row['Email Preview']]
                subject = row['Email Subject']
                send_email(receiver_email, message_text_list, subject)
            
            st.success("Emails sent successfully!")


# PAGE: Run Night Actions
elif page == 'Run Night Actions':
    st.header('Run Night Actions')
    st.write('Run the night actions and resolve outcomes.')

    if 'night_preview_df' not in st.session_state:
        st.session_state['night_preview_df'] = pd.DataFrame()

    if st.button('Preview Night Actions'):
        st.session_state['night_preview_df'] = game.run_night(preview_only=True)
        st.dataframe(st.session_state['night_preview_df'])

    if not st.session_state['night_preview_df'].empty:
        if st.button('Confirm and Send Night Results'):
            _ = game.run_night(preview_only=False)
            st.success('Night Results Sent')


# --- PAGE: Voting Phase ---
elif page == 'Voting Phase':
    st.header('🗳️ Voting Phase')
    st.write('Process the daytime voting to eliminate a player.')

    if st.button('Run Voting'):
        game.run_voting()
        st.success('Voting phase complete!')

    if hasattr(game, 'vote_results'):
        st.subheader('Vote Results')
        st.write(game.vote_results)

# --- PAGE: Utilities ---
elif page == 'Utilities':
    st.header('🧰 Utilities')

    st.subheader('👑 Reveal Mayor')
    mayor_name = st.text_input('Enter player name:')
    if st.button('Reveal Mayor'):
        if mayor_name:
            game.reveal_mayor(mayor_name)
            st.success(f'{mayor_name} has revealed as Mayor.')
        else:
            st.warning('Please enter a player name.')

    st.subheader('🕵️ Assign New Godfather')
    if st.button('Assign New Godfather'):
        game.assign_new_godfather()
        st.success('New Godfather assigned!')


# PAGE: View Files
elif page == 'View Files':
    st.header('View Saved Files')
    # List CSV files
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    csv_files.sort()

    if not csv_files:
        st.warning("No saved CSV files found in the Game Data folder.")
    else:
        # Display filenames without full path for clarity
        file_names = [os.path.basename(f) for f in csv_files]

        selected_file = st.selectbox("Choose a file to view", file_names)

        # Load and show the selected file
        if selected_file:
            file_path = os.path.join(DATA_DIR, selected_file)
            df = pd.read_csv(file_path)
            st.subheader(f"Contents of {selected_file}")
            st.dataframe(df)