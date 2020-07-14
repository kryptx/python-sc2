from typing import Union

from .bot_ai import BotAI
from .data import AIBuild, Difficulty, PlayerType, Race


class AbstractPlayer:
    def __init__(self, p_type, race=None, name=None, difficulty=None, ai_build=None, fullscreen=False):
        assert isinstance(p_type, PlayerType), f"p_type is of type {type(p_type)}"
        assert name is None or isinstance(name, str), f"name is of type {type(name)}"

        self.name = name
        self.type = p_type
        self.fullscreen = fullscreen
        if race is not None:
            self.race = race
        if p_type == PlayerType.Computer:
            assert isinstance(difficulty, Difficulty), f"difficulty is of type {type(difficulty)}"
            # Workaround, proto information does not carry ai_build info
            # We cant set that in the Player classmethod
            assert ai_build is None or isinstance(ai_build, AIBuild), f"ai_build is of type {type(ai_build)}"
            self.difficulty = difficulty
            self.ai_build = ai_build

        elif p_type == PlayerType.Observer:
            assert race is None
            assert difficulty is None
            assert ai_build is None

        else:
            assert isinstance(race, Race), f"race is of type {type(race)}"
            assert difficulty is None
            assert ai_build is None

    @property
    def needs_sc2(self):
        return not isinstance(self, Computer)


class Human(AbstractPlayer):
    def __init__(self, race, name=None, fullscreen=False):
        super().__init__(PlayerType.Participant, race, name=name, fullscreen=fullscreen)

    def __str__(self):
        if self.name is not None:
            return f"Human({self.race._name_}, name={self.name !r})"
        else:
            return f"Human({self.race._name_})"


class Bot(AbstractPlayer):
    def __init__(self, race, ai, name=None, fullscreen=False):
        """
        AI can be None if this player object is just used to inform the
        server about player types.
        """
        assert isinstance(ai, BotAI) or ai is None, f"ai is of type {type(ai)}, inherit BotAI from bot_ai.py"
        super().__init__(PlayerType.Participant, race, name=name, fullscreen=fullscreen)
        self.ai = ai

    def __str__(self):
        if self.name is not None:
            return f"Bot {self.ai.__class__.__name__}({self.race._name_}), name={self.name !r})"
        else:
            return f"Bot {self.ai.__class__.__name__}({self.race._name_})"


class Computer(AbstractPlayer):
    def __init__(self, race, difficulty=Difficulty.Easy, ai_build=AIBuild.RandomBuild):
        super().__init__(PlayerType.Computer, race, difficulty=difficulty, ai_build=ai_build)

    def __str__(self):
        return f"Computer {self.difficulty._name_}({self.race._name_}, {self.ai_build.name})"


class Observer(AbstractPlayer):
    def __init__(self):
        super().__init__(PlayerType.Observer)

    def __str__(self):
        return f"Observer"


class Player(AbstractPlayer):
    @classmethod
    def from_proto(cls, proto):
        if PlayerType(proto.type) == PlayerType.Observer:
            return cls(proto.player_id, PlayerType(proto.type), None, None, None)
        return cls(
            proto.player_id,
            PlayerType(proto.type),
            Race(proto.race_requested),
            Difficulty(proto.difficulty) if proto.HasField("difficulty") else None,
            Race(proto.race_actual) if proto.HasField("race_actual") else None,
            proto.player_name if proto.HasField("player_name") else None,
        )

    def __init__(self, player_id, p_type, requested_race, difficulty=None, actual_race=None, name=None, ai_build=None):
        super().__init__(p_type, requested_race, difficulty=difficulty, name=name, ai_build=ai_build)
        self.id: int = player_id
        self.actual_race: Race = actual_race


class BotProcess(AbstractPlayer):
    """
    Class for handling bots launched externally, including non-python bots.
    Default parameters comply with sc2ai and ai-arena ladders.

    :param path: the executable file's path
    :param launch_str: the cmd-line string that launches the bot e.g. 'python run.py' or 'run.exe'
    :param race: bot's race
    :param name: bot's name
    :param sc2port_arg: the accepted argument name for the port of the sc2 instance to listen to
    :param hostaddress_arg: the accepted argument name for the address of the sc2 instance to listen to
    :param match_arg: the accepted argument name for the starting port to generate a portconfig from
    :param realtime_arg: the accepted argument name for specifying realtime
    :param other_args: anything else that is needed

    e.g. to call a bot capable of running on the bot ladders:
        BotProcess(os.getcwd(), "python run.py", Race.Terran, "INnoVation")
    """

    def __init__(
            self,
            path: str,
            launch_str: str,
            race: Race,
            name=None,
            sc2port_arg="--GamePort",
            hostaddress_arg="--LadderServer",
            match_arg="--StartPort",
            realtime_arg="--Realtime",
            other_args: str=None,
            stdout: str=None,
    ):
        self.race = race
        self.type = PlayerType.Participant
        self.name = name

        self.path = path
        self.launch_str = launch_str
        self.sc2port_arg = sc2port_arg
        self.match_arg = match_arg
        self.hostaddress_arg = hostaddress_arg
        self.realtime_arg = realtime_arg
        self.other_args = other_args
        self.stdout = stdout
        if stdout is None:
            self.stdout = launch_str

    def __repr__(self):
        if self.name is not None:
            return f"Bot {self.name}({self.race.name} from {self.launch_str})"
        else:
            return f"Bot({self.race.name} from {self.launch_str})"

    def cmd_line(self, sc2port: Union[int, str], matchport: Union[int, str], hostaddress: str, realtime: str=None):
        """

        :param sc2port: the port that the launched sc2 instance listens to
        :param matchport: some starting port that both bots use to generate identical portconfigs
        :param hostaddress: the address the sc2 instances used
        :param realtime: 1 or 0, indicating whether the match is played in realtime or not
        :return: string that will be used to start the bot's process
        """
        cmd_line = [
            self.launch_str,
            self.sc2port_arg, str(sc2port),
            self.match_arg, str(matchport),
            self.hostaddress_arg, hostaddress,
        ]
        if self.other_args is not None:
            cmd_line.append(self.other_args)
        if realtime is not None:
            cmd_line.extend([self.realtime_arg, str(realtime)])
        return " ".join(cmd_line)


