from vacuum_agent.liuvacuum import *
import copy

DEBUG_OPT_DENSEWORLDMAP = False

AGENT_STATE_UNKNOWN = 0
AGENT_STATE_WALL = 1
AGENT_STATE_CLEAR = 2
AGENT_STATE_DIRT = 3
AGENT_STATE_HOME = 4

AGENT_DIRECTION_NORTH = 0
AGENT_DIRECTION_EAST = 1
AGENT_DIRECTION_SOUTH = 2
AGENT_DIRECTION_WEST = 3

def direction_to_string(cdr):
    cdr %= 4
    return  "NORTH" if cdr == AGENT_DIRECTION_NORTH else\
            "EAST"  if cdr == AGENT_DIRECTION_EAST else\
            "SOUTH" if cdr == AGENT_DIRECTION_SOUTH else\
            "WEST" #if dir == AGENT_DIRECTION_WEST

"""
Internal state of a vacuum agent
"""
class MyAgentState:

    def __init__(self, width, height):

        # Initialize perceived world state
        self.world = [[AGENT_STATE_UNKNOWN for _ in range(height)] for _ in range(width)]
        self.world[1][1] = AGENT_STATE_HOME

        # Mark outer border of the world as walls
        for i in range(height):
            self.world[0][i] = AGENT_STATE_WALL
            self.world[width - 1][i] = AGENT_STATE_WALL
        for i in range(width):
            self.world[i][0] = AGENT_STATE_WALL
            self.world[i][height - 1] = AGENT_STATE_WALL    

        # Agent internal state
        self.last_action = ACTION_NOP
        self.direction = AGENT_DIRECTION_EAST
        self.pos_x = 1
        self.pos_y = 1

        # Metadata
        self.world_width = width
        self.world_height = height

    """
    Update perceived agent location
    """
    def update_position(self, bump):
        if not bump and self.last_action == ACTION_FORWARD:
            if self.direction == AGENT_DIRECTION_EAST:
                self.pos_x += 1
            elif self.direction == AGENT_DIRECTION_SOUTH:
                self.pos_y += 1
            elif self.direction == AGENT_DIRECTION_WEST:
                self.pos_x -= 1
            elif self.direction == AGENT_DIRECTION_NORTH:
                self.pos_y -= 1

    """
    Update perceived or inferred information about a part of the world
    """
    def update_world(self, x, y, info):
        self.world[x][y] = info

    """
    Dumps a map of the world as the agent knows it
    """
    def print_world_debug(self):
        for y in range(self.world_height):
            for x in range(self.world_width):
                if self.world[x][y] == AGENT_STATE_UNKNOWN:
                    print("?" if DEBUG_OPT_DENSEWORLDMAP else " ? ", end="")
                elif self.world[x][y] == AGENT_STATE_WALL:
                    print("#" if DEBUG_OPT_DENSEWORLDMAP else " # ", end="")
                elif self.world[x][y] == AGENT_STATE_CLEAR:
                    print("." if DEBUG_OPT_DENSEWORLDMAP else " . ", end="")
                elif self.world[x][y] == AGENT_STATE_DIRT:
                    print("D" if DEBUG_OPT_DENSEWORLDMAP else " D ", end="")
                elif self.world[x][y] == AGENT_STATE_HOME:
                    print("H" if DEBUG_OPT_DENSEWORLDMAP else " H ", end="")

            print() # Newline
        print() # Delimiter post-print

    """
    Updates the direction and last_action for a turning action and returns the action
    """
    def turn_action(self, action):
        if action == ACTION_TURN_LEFT:
            self.last_action = action
            self.direction = (self.direction - 1) % 4
            return action
        elif action == ACTION_TURN_RIGHT:
            self.last_action = action
            self.direction = (self.direction + 1) % 4
            return action
        else:
            print("Entered invalid action, doing nothing.")


"""
Vacuum agent
"""
class MyVacuumAgent(Agent):

    def __init__(self, world_width, world_height, log):
        super().__init__(self.execute)
        self.initial_random_actions = 10
        self.iteration_counter = 2*(world_height*world_width)
        self.state = MyAgentState(world_width, world_height)
        self.log = log
        self.action_queue = []
        self.finished_cleaning = False

    def move_to_random_start_position(self, bump):
        action = random()

        self.initial_random_actions -= 1
        self.state.update_position(bump)

        if action < 0.1666666:   # 1/6 chance
            self.state.direction = (self.state.direction + 3) % 4
            self.state.last_action = ACTION_TURN_LEFT
            return ACTION_TURN_LEFT
        elif action < 0.3333333: # 1/6 chance
            self.state.direction = (self.state.direction + 1) % 4
            self.state.last_action = ACTION_TURN_RIGHT
            return ACTION_TURN_RIGHT
        else:                    # 4/6 chance
            self.state.last_action = ACTION_FORWARD
            return ACTION_FORWARD

    def execute(self, percept):

        bump = percept.attributes["bump"]
        dirt = percept.attributes["dirt"]
        home = percept.attributes["home"]

        # Move agent to a randomly chosen initial position
        if self.initial_random_actions > 0:         
            self.log("Moving to random start position ({} steps left)".format(self.initial_random_actions))
            return self.move_to_random_start_position(bump)

        # Finalize randomization by properly updating position (without subsequently changing it)
        elif self.initial_random_actions == 0:
            self.initial_random_actions -= 1
            self.state.update_position(bump)
            self.state.last_action = ACTION_SUCK
            self.log("Processing percepts after position randomization")
            return ACTION_SUCK


        # Max iterations for the agent
        if self.iteration_counter < 1:
            if self.iteration_counter == 0:
                self.iteration_counter -= 1
                self.log("Iteration counter is now 0. Halting!")
                self.log("Performance: {}".format(self.performance))
            return ACTION_NOP

        self.iteration_counter -= 1

        # Track position of agent
        self.state.update_position(bump)

        self.log("Position: ({}, {})\t\tDirection: {}".format(self.state.pos_x, self.state.pos_y, 
                                                        direction_to_string(self.state.direction)))
        
        if bump:
            # Get an xy-offset pair based on where the agent is facing
            offset = [(0, -1), (1, 0), (0, 1), (-1, 0)][self.state.direction]

            # Mark the tile at the offset from the agent as a wall (since the agent bumped into it)
            self.state.update_world(self.state.pos_x + offset[0], self.state.pos_y + offset[1], AGENT_STATE_WALL)

        # Update perceived state of current tile
        if dirt:
            self.state.update_world(self.state.pos_x, self.state.pos_y, AGENT_STATE_DIRT)
        else:
            self.state.update_world(self.state.pos_x, self.state.pos_y, AGENT_STATE_CLEAR)  

        # Debug
        self.state.print_world_debug()

        # Decide action
        if dirt:
            self.log("DIRT -> choosing SUCK action!")
            self.state.last_action = ACTION_SUCK
            return ACTION_SUCK  

        # Special case for if all squares have been visited: find path to home position of robot
        if self.all_squares_visited_check() or self.finished_cleaning:
            print("All squares are visited, going home.")
            if home:   
                print("Finished cleaning and returned to home! Setting iterations to 0, shutting down...")
                self.log("Finished cleaning and returned to home!")
                self.iteration_counter = 0
                self.state.last_action = ACTION_NOP
                return ACTION_NOP
            elif not self.action_queue:
                print("Generating path to home...")
                self.action_queue = self.breadth_first_search(AGENT_STATE_HOME)
                print("Next action(s) to home = " + str(self.action_queue))

        # otherwise get new actions of robot bumps into wall or if action queue is empty
        elif bump or not self.action_queue:
                print("GENERATING NEW ACTION QUEUE...")
                self.action_queue = self.breadth_first_search(AGENT_STATE_UNKNOWN)
                # if empty queue was returned, it means that bfs could not find any unkown square -> go home
                if not self.action_queue:
                    print("No reachable unkown squares could be found, planning to home position.")
                    self.finished_cleaning = True
                    self.action_queue = self.breadth_first_search(AGENT_STATE_HOME)
                print("Next action(s) = " + str(self.action_queue))

        # if there are actions in the action queue, execute this
        if self.action_queue:
            self.state.last_action = self.action_queue.pop(0)
            if (self.state.last_action == ACTION_TURN_LEFT) or (self.state.last_action == ACTION_TURN_RIGHT):
                self.state.turn_action(self.state.last_action)
            return self.state.last_action


    """
    Perform breadth first search to find the next square with desired state (e.g home, dirt or unknown)
    Returns action queue (how to reach the square)
    """
    def breadth_first_search(self, agent_state):
        #######################################################
         #  A node is a list item with the following structure: 
         #  node[0] = x coordinate of the agent
         #  node[1] = y coordinate of the agent
         #  node[2] = direction of the agent
         #  node[3] = the action queue (also a list)
        #######################################################
        node = [self.state.pos_x, self.state.pos_y, self.state.direction, []]
        frontier = []
        reached = []
        if self.goal_check(node[0], node[1], agent_state):
            return node[3]
        frontier.append(node)
        reached.append([node[0], node[1]])
        children = []
        while len(frontier) > 0:
            node = frontier.pop(0)
            children = self.expand(node)
            for child in children:
                s = [child[0], child[1]]
                ## early goal check : check for unkown square / home square during node generation (defined by agent_state)
                if self.goal_check(s[0], s[1], agent_state):
                    return child[3]
                if not s in reached:
                    reached.append(s)
                    frontier.append(child)

        print("Could not find path to desired square.")
        return None


    """
    This is the expand(problem, node) function 
    It simulates possible actions (squares in front of, left, right and behind agent) and returnes the reachable children
    Because of early goal check (check during node generation instead of node expansion), the square right in front of the 
    agent is most likely picked, which is good because least actions are required (only forward instead of turn + forward)
    """
    def expand(self, parent):
        #########################################################
         #  A child is a list item with the following structure: 
         #  child[0] = x coordinate
         #  child[1] = y coordinate
         #  child[2] = direction
         #  child[3] = the action queue (also a list)
        ######################################################### 
        children = []   # where generated children will be stored

        ## go forward action
        child = copy.deepcopy(parent)      
        child[3].append(ACTION_FORWARD)
        dir = child[2]
        if dir == AGENT_DIRECTION_EAST:
            child[0] += 1
        elif dir == AGENT_DIRECTION_SOUTH:
            child[1] += 1
        elif dir == AGENT_DIRECTION_WEST:
            child[0] -= 1
        elif dir == AGENT_DIRECTION_NORTH:
            child[1] -= 1

        # the square cannot be a wall! only append to graph if the agent can actually go there
        if not self.goal_check(child[0], child[1], AGENT_STATE_WALL):  
            children.append(child[:])

        ## turn left action
        child = copy.deepcopy(parent)
        child[3].append(ACTION_TURN_LEFT)
        child[3].append(ACTION_FORWARD)
        child[2] = (child[2] - 1) % 4
        dir = child[2]
        if dir == AGENT_DIRECTION_EAST:
            child[0] += 1
        elif dir == AGENT_DIRECTION_SOUTH:
            child[1] += 1
        elif dir == AGENT_DIRECTION_WEST:
            child[0] -= 1
        elif dir == AGENT_DIRECTION_NORTH:
            child[1] -= 1

        if not self.goal_check(child[0], child[1], AGENT_STATE_WALL):  
            children.append(child[:]) 

        ## turn right action
        child = copy.deepcopy(parent)
        child[3].append(ACTION_TURN_RIGHT)
        child[3].append(ACTION_FORWARD)
        child[2] = (child[2] + 1) % 4
        dir = child[2]
        if dir == AGENT_DIRECTION_EAST:
            child[0] += 1
        elif dir == AGENT_DIRECTION_SOUTH:
            child[1] += 1
        elif dir == AGENT_DIRECTION_WEST:
            child[0] -= 1
        elif dir == AGENT_DIRECTION_NORTH:
            child[1] -= 1

        if not self.goal_check(child[0], child[1], AGENT_STATE_WALL):  
            children.append(child[:])

        ## go backwards action
        child = copy.deepcopy(parent)
        child[3].append(ACTION_TURN_RIGHT)
        child[3].append(ACTION_TURN_RIGHT)
        child[3].append(ACTION_FORWARD)
        child[2] = (child[2] + 2) % 4
        dir = child[2]
        if dir == AGENT_DIRECTION_EAST:
            child[0] += 1
        elif dir == AGENT_DIRECTION_SOUTH:
            child[1] += 1
        elif dir == AGENT_DIRECTION_WEST:
            child[0] -= 1
        elif dir == AGENT_DIRECTION_NORTH:
            child[1] -= 1

        if not self.goal_check(child[0], child[1], AGENT_STATE_WALL):  
            children.append(child[:])   

        return children


    """
    Checks if all squares in the map have been visited 
    Returns true if all squares have been visited, Returns false if there are still unkown squares
    """
    def all_squares_visited_check(self):
        for y in range(self.state.world_height):
            for x in range(self.state.world_width):
                if self.state.world[x][y] == AGENT_STATE_UNKNOWN:
                    return False         
        return True    


    """
    Checks whether a position corresponds to a desired state (e.g. wall, home or unknown)
    Returns true if it does, false otherwise
    """
    def goal_check(self, x, y, agent_state):
        if agent_state == AGENT_STATE_HOME:
            if (x == 1) and (y == 1):
                return True
            else:
                return False    

        elif agent_state == AGENT_STATE_UNKNOWN:
            if self.state.world[x][y] == AGENT_STATE_UNKNOWN:
                return True
            else:
                return False   

        elif agent_state == AGENT_STATE_WALL:
            if self.state.world[x][y] == AGENT_STATE_WALL:
                return True
            else:
                return False    

        elif agent_state == AGENT_STATE_DIRT:
            if self.state.world[x][y] == AGENT_STATE_DIRT:
                return True
            else:
                return False  

        else:
            print("Entered invalid agent state.")
            return False