import random

# Wrapper to make sure player is alive and has a target who is alive before attempting to do an action
# Also increments actions_used if there is a valid target
def check_target(action):
    def wrapper(self, *args, **kwargs):
        if self.get_target() is None:
            return
        if self.dead == True:
            return
        if self.get_target().dead == True:
            return
        self.actions_used += 1
        return action(self, *args, **kwargs)
    return wrapper

def check_target2(action):
    def wrapper(self, *args, **kwargs):
        if self.get_target2() is None:
            return
        if self.dead == True:
            return
        if self.get_target().dead == True:
            return
        return action(self, *args, **kwargs)
    return wrapper

# Same as check_target but will not increment actions_used. Used in classes with an end_action that I do not want to double count as an action
def check_target_no_increment(action):
    def wrapper(self, *args, **kwargs):
        if self.get_target() is None:
            return
        if self.dead == True:
            return
        if self.get_target().dead == True:
            return
        return action(self, *args, **kwargs)
    return wrapper

# Probably a better way to do this besides a whole extra wrapper
def check_target_arso(action):
    def wrapper(self, *args, **kwargs):
        if self.arso_action in ['Douse', 'Undouse']:
            if self.get_target() is None:
                return
            if self.dead:
                return
            if self.get_target().dead:
                return
            self.actions_used += 1
        return action(self, *args, **kwargs)
    return wrapper

# Probably a better way to do this besides a whole extra wrapper
def check_target_MM(action):
    def wrapper(self, *args, **kwargs):
        if self.get_target() is None:
            self.actions_used = 0
            return
        if self.dead == True:
            self.actions_used = 0
            return
        if self.get_target().dead == True:
            self.actions_used = 0
            return
        self.actions_used = 1
        return action(self, *args, **kwargs)
    return wrapper

# For roles with non targeting abilities, if there is a target then remove the target so it is not seen by follow/watch and then run the action
def check_target_NTA(action):
    def wrapper(self, *args, **kwargs):
        if self.get_target() is None:
            return
        self.remove_target()
        self.actions_used += 1
        return action(self, *args, **kwargs)
    return wrapper

# Wrapper to check player has actions left to use
def check_num_actions(select):
    def wrapper(self, *args, **kwargs):
        if self.actions_used >= self.number_actions:
            return
        return select(self, *args, **kwargs)
    return wrapper
    

# Super class for all roles
class Role:
    is_guilty = False
    is_lethal = False
    roleblock_immune = False
    control_immune = False
    defence_level = 0
    attack_level = 0
    number_actions = 10^4

    def __init__(self, name, email, player_dict = None, dead = False, actions_used = 0, doused = 0, sabotaged = 0, marked = 0, revealed_mayor = 0):
        self.name = name
        self.email = email
        self.attacked_by = []
        self.player_dict = player_dict
        self.dead = dead
        self.died_tonight = False
        self.cleaned = False
        self.doused = doused
        self.corrupted = False
        self.sabotaged = sabotaged
        self.marked = marked
        self.revealed_mayor = revealed_mayor
        self.actions_used = actions_used
        self.night_result = []

    # Set a player's target while adding the player to the list of people targeting the player targeted
    @check_num_actions
    def select_target(self, target):
        if target != None:
            self.player_dict[self].append(target)

    # Remove the target from a player
    def remove_target(self):
        if self.get_target():
            self.player_dict[self] = []

    def get_target(self):
        if len(self.player_dict[self]) > 0:
            return self.player_dict[self][0]
        else:
            return None
    
    def targeted_by(self):
        targeted_by_list = []
        for player, target_list in self.player_dict.items():
            for target in target_list:
                if target == self:
                    targeted_by_list.append(player)
        return targeted_by_list

    def get_name(self):
        return self.name
    
    def get_email(self):
        return self.email
    
    def get_defence_level(self):
        return self.defence_level
    
    def die(self):
        self.died_tonight = True
        self.add_result('You died')
    
    def attack(self, victim):
        if self.attack_level > victim.get_defence_level():
            self.add_result('You attacked and killed ' + victim.get_name())
            victim.die()
        else:
            self.add_result('You tried to attack ' + victim.get_name() + ' but they survived the attack')
            victim.add_result('You were attacked but survived')
        victim.attacked_by.append(self)

    def add_result(self, message):
        self.night_result.append(message)
    
    def get_results(self):
        return self.night_result
    
# Intermediary class for Town roles
class Town(Role):
    faction = 'Town'

# Intermediary class for Mafia roles
class Mafia(Role):
    faction = 'Mafia'
    is_guilty = True

# Intermediary class for Neutral roles
class Neutral(Role):
    faction = 'Neutral'


# For roles with two targets
class Two_targeter:
    def select_target2(self, target2):
        if target2 != None:
            self.player_dict[self].append(target2)

    def get_target2(self):
        if len(self.player_dict[self]) > 1:
            return self.player_dict[self][1]
        else:
            return None


class Driver(Two_targeter):
    roleblock_immune = True
    control_immune = True

    # Swap players
    @check_target
    @check_target2
    def perform_action(self):
        target1 = self.get_target()
        target2 = self.get_target2()
        
        for player, target_list in self.player_dict.items():
            if player != self:
                if len(target_list) > 0:
                    if target_list[0] == target1:
                        self.player_dict[player][0] = target2
                    elif target_list[0] == target2:
                        self.player_dict[player][0] = target1
                    
                if len(target_list) > 1:
                    if target_list[1] == target1:
                        self.player_dict[player][1] = target2
                    elif target_list[1] == target2:
                        self.player_dict[player][1] = target1

        target1.add_result('You were swapped')
        target2.add_result('You were swapped')
        self.add_result(f'You swapped {target1.get_name()} and {target2.get_name()}')


class Seducer:
    roleblock_immune = True
    
    # Seduce
    @check_target
    def perform_action(self):
        if self.get_target().roleblock_immune == False:
            self.get_target().remove_target()
            self.add_result('You seduced ' + self.get_target().get_name())
            self.get_target().add_result('You were seduced by an Escort or Hooker and forgot to perform your action')
        else:
            self.add_result('You attempted to seduce ' + self.get_target().get_name() + ' but failed')
            self.get_target().add_result('An Escort or Hooker attempted to seduce you')


class Follower:
    # Follow
    @check_target
    def perform_action(self):
        if self.get_target().get_target() is not None and str(type(self.get_target()).__name__) != 'Amnesiac':
            self.add_result('You followed ' + self.get_target().get_name() + ' to ' + self.get_target().get_target().get_name())
        else:
            self.add_result('You followed ' + self.get_target().get_name() + ' to no one')


class Watch:
    # Watch
    @check_target
    def perform_action(self):
        temp_targeted_by = [player for player in self.get_target().targeted_by() if player != self and player != self.get_target()]
        if temp_targeted_by:
            message = 'You watched ' + self.get_target().get_name() + ' and they were visited by '
            for i in range(len(temp_targeted_by)):
                message = message + temp_targeted_by[i].get_name()
                if i != len(temp_targeted_by) - 1:
                    message = message + ' and '
            self.add_result(message)
        else:
            self.add_result('You watched ' + self.get_target().get_name() + ' and they were visited by no one')


class Mayor(Town):
    number_actions = 0


class Cop(Town):
    # Investigate
    @check_target
    def perform_action(self):
        if self.get_target().is_guilty:
            self.add_result('You investigated ' + self.get_target().get_name() + ' and found they were guilty')
        else:
            self.add_result('You investigated ' + self.get_target().get_name() + ' and found they were innocent')


class Doctor(Town):
    # Give defence
    @check_target_no_increment
    def perform_action(self):
        # Temporary solution. Will only increment actions_used if self targeted and will prevent self targeting after that
        if self.get_target() == self and self.actions_used < 1:
            self.get_target().defence_level = 1
            self.actions_used += 1
        elif self.get_target() != self:
            self.get_target().defence_level = 1

    # Create messages
    @check_target_no_increment
    def end_action(self):
        temp_attack_1 = [player for player in self.get_target().attacked_by if player.attack_level == 1]
        if temp_attack_1:
            for attacker in temp_attack_1:
                self.add_result('You successfully protected ' + self.get_target().get_name() + ' from an attack')
        else:
            self.add_result('You protected ' + self.get_target().get_name() + ' but did not save them from anything')


class Bus_driver(Driver, Town):
    pass


class Tracker(Follower, Town):
    pass


class Watcher(Watch, Town):
    pass


class Escort(Seducer, Town):
    pass


class Vigilante(Town):
    is_guilty = True
    is_lethal = True
    attack_level = 1
    number_actions = 3

    # Slay
    @check_target
    def perform_action(self):
        self.attack(self.get_target())


class Veteran(Town):
    is_lethal = True
    roleblock_immune = True
    control_immune = True
    attack_level = 2
    number_actions = 3

    # On guard
    @check_target_NTA
    def perform_action(self):
        temp_targeted_by = [player for player in self.targeted_by() if player != self]
        self.defence_level = 1
        for visitor in temp_targeted_by:
            self.attack(visitor)


class Bomb(Town):
    is_lethal = True
    attack_level = 2
    number_actions = 0

    # Explode
    def end_action(self):
        if self.attacked_by:
            for attacker in self.attacked_by:
                self.attack(attacker)

class Bodyguard(Town):
    is_lethal = True
    attack_level = 2

    # Giving defence
    @check_target
    def perform_action(self):
        if self.get_target() != self:
            self.get_target().defence_level = 1

    # Counter attack
    @check_target_no_increment
    def end_action(self):
        temp_attacked_by = [player for player in self.get_target().attacked_by]
        self.add_result('You defended ' + self.get_target().get_name())
        if temp_attacked_by:
            for attacker in temp_attacked_by:
                self.attack(attacker)
            self.die()


class Detective(Town):
    # Scrutinize
    @check_target
    def perform_action(self):
        if self.get_target().is_lethal:
            self.add_result('You scrutinized ' + self.get_target().get_name() + ' and found they were lethal')
        else:
            self.add_result('You scrutinized ' + self.get_target().get_name() + ' and found they were non-lethal')


class Mafioso(Mafia):
    number_actions = 0


class Godfather(Mafia):
    is_guilty = False
    is_lethal = True
    attack_level = 1

    # Assassinate
    @check_target
    def perform_action(self):
        self.attack(self.get_target())


class Limo_driver(Driver, Mafia):
    pass


class Stalker(Follower, Mafia):
    pass


class Lookout(Watch, Mafia):
    pass


class Hooker(Seducer, Mafia):
    pass


class Janitor(Mafia):
    number_actions = 1

    # Dispose
    @check_target
    def perform_action(self):
        self.get_target().cleaned = True

    # Give janitor the role of cleaned person
    @check_target_no_increment
    def end_action(self):
        if self.get_target().died_tonight == True:
            self.add_result('You cleaned ' + self.get_target().get_name() + ' and their role was ' + str(type(self.get_target()).__name__))
        else:
            self.actions_used -= 1


class Framer(Mafia):
    # Frame
    @check_target
    def perform_action(self):
        self.get_target().is_guilty = True


class Yakuza(Mafia):
    random_mafia = ['Limo_driver', 'Stalker', 'Lookout', 'Hooker', 'Janitor', 'Framer', 'Saboteur', 'Sniper']
    def __init__(self, name, email, player_dict=None, dead=False, actions_used=0, doused=0, sabotaged=0, marked=0, revealed_mayor=0):
        super().__init__(name, email, player_dict, dead, actions_used, doused, sabotaged, marked, revealed_mayor)
        self.revealed_role = 'Yakuza'

    # Corrupt
    @check_target
    def end_action(self):
        if issubclass(type(self.get_target()), Mafia):
            self.add_result('You tried to corrupt ' + self.get_target().get_name() + ' but they are part of the mafia')
        elif 1 > self.get_target().get_defence_level():
            if not self.get_target().attacked_by:
                self.die()
                self.revealed_role = random.choice(self.random_mafia)
                self.add_result('You converted ' + self.get_target().get_name())
                self.get_target().corrupted = True
                self.get_target().add_result('You were converted by a yakuza')
            else:
                self.add_result('You tried to corrupt ' + self.get_target().get_name() + ' but they died tonight')
        else:
            self.add_result('You tried to corrupt ' + self.get_target().get_name() + ' but they were protected')
            self.get_target().add_result('A Yakuza attempted to corrupt you, but you were protected')


class Saboteur(Mafia):
    is_lethal = True

    # Sabotage
    @check_target
    def perform_action(self):
        self.get_target().sabotaged = 1

class Sniper(Mafia):
    is_lethal = True
    attack_level = 2
    number_actions = 1

    # Snipe
    @check_target
    def perform_action(self):
        self.attack(self.get_target())


class Jester(Neutral):
    number_actions = 0
    

class Serial_killer(Neutral):
    faction = 'Lethal neutral'
    is_lethal = True
    defence_level = 1
    attack_level = 1

    # Slaughter
    @check_target
    def perform_action(self):
        self.attack(self.get_target())


class Mass_murderer(Neutral):
    faction = 'Lethal neutral'
    is_lethal = True
    defence_level = 1
    attack_level = 1
    number_actions = 1

    # Ambush
    @check_target_MM
    def perform_action(self):
        self.add_result('You ambushed at ' + self.get_target().get_name() + '\'s house')
        temp_targeted_by = [player for player in self.get_target().targeted_by() if player != self]
        if temp_targeted_by:
            for i in range(len(temp_targeted_by)):
                self.attack(temp_targeted_by[i])
        if self.get_target().get_target() == None:
            self.attack(self.get_target())


class Arsonist(Neutral):
    faction = 'Lethal neutral'
    is_lethal = True
    defence_level = 1
    attack_level = 2
    number_actions = 10^4
    arso_action = 'Douse'

    @check_target_arso
    def perform_action(self):
        # Douse
        if self.arso_action == 'Douse':
            self.get_target().doused = 1
            self.add_result('You doused ' + self.get_target().get_name())
            self.get_target().add_result('You were doused by an Arsonist')
        # Undouse
        if self.arso_action == 'Undouse':
            self.get_target().doused = 0
            self.add_result('You undoused ' + self.get_target().get_name())
            self.get_target().add_result('You were undoused by an Arsonist')
        # Ignite
        if self.arso_action == 'Ignite':
            for player in self.player_dict:
                if player.doused == 1:
                    player.die()
                    self.add_result('You ignited ' + player.get_name())


class Witch(Neutral, Two_targeter):
    roleblock_immune = True
    control_immune = True

    # Control
    @check_target
    @check_target2
    def perform_action(self):
        if self.get_target().control_immune == False:
            self.get_target().remove_target()
            self.get_target().select_target(self.get_target2())
            self.add_result('You controlled ' + self.get_target().get_name() + ' to ' + self.get_target2().get_name())
            self.get_target().add_result('You were controlled')
        # Removing second target to not be seen by watcher
        if self.get_target():
            self.player_dict[self] = [self.player_dict[self][0]]


class Amnesiac(Neutral):
    def __init__(self, name, email, player_dict=None, dead=False, actions_used=0, doused=0, sabotaged=0, marked=0, revealed_mayor=0):
        super().__init__(name, email, player_dict, dead, actions_used, doused, sabotaged, marked, revealed_mayor)
        self.remembered_role = 'Amnesiac'

    # Remember
    def perform_action(self):
        if self.get_target() is None or self.get_target().dead == False or str(type(self.get_target()).__name__) == 'Godfather':
            return
        self.remembered_role = str(type(self.get_target()).__name__)
        self.add_result('You remembered you were a ' + self.remembered_role)
        # Telling the amnesiac the mafia if they remember a non-saboteur mafia role
        revealed_mafia_list = ['Godfather', 'Lookout', 'Framer', 'Sniper', 'Yakuza', 'Janitor', 'Limo Driver', 'Hooker', 'Stalker', 'Sniper']
        mafia_names = 'The mafia members are'
        if self.remembered_role in revealed_mafia_list:
            for player in self.player_dict:
                if str(type(player).__name__) in revealed_mafia_list:
                    mafia_names = mafia_names + ' ' + player.get_name()
                    player.add_result(self.get_name() + ' joined the mafia as a ' + self.remembered_role)
            self.add_result(mafia_names)


class Survivor(Neutral):
    control_immune = True
    number_actions = 4
    
    # Bulletproof vest
    @check_target_NTA
    def perform_action(self):

        self.defence_level = 1
        self.add_result('You used a bulletproof vest')
