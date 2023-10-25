import argparse
import pandas as pd
import sys

from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable
from os import name
from subprocess import run

#################### CONSTANTS ####################
DEFAULT_INPUT_FILE = "2023-24/Nov MML Data.csv"
DEFAULT_OUTPUT_FILE = "output/Nov 2023-24 Selection.csv"
N_ROUNDS = 6

#################### FUNCTIONALITY ####################
# Command to clear the terminal
def clear():
    if name == 'nt': # Windows
        run('cls', shell=True)
    else: # Everything else
        run('clear', shell=True)

def main(args):
    # Clears the terminal if the -c argument equals 'y'
    if args.c:
        clear()
    
    # Whether to print diagnostic information
    verbose = args.v

    # Get the file from arguments, or the November MML if the user forgets the argument
    file = args.i if args.i else DEFAULT_INPUT_FILE

    # Load the CSV
    data = pd.read_csv(file)

    # Format the DataFrame
    if 'Name' not in data:
        data['Name'] = data['First Name'] + ' ' + data['Last Name']
    data.drop('First Name', axis=1, inplace=True)
    data.drop('Last Name', axis=1, inplace=True)

    # Record how many members there are
    size = len(data)

    # Make every round for every member a binary (0 or 1) variable 
    variables = []
    for member in range(size):
        variables.append([LpVariable(name=f"{data.iloc[member, 6]}|{r+1}", lowBound=0, cat='Binary') for r in range(N_ROUNDS)])

    # Convert the data to an objective function
    objective_function = []
    for i in range(size):
        objective_function += [variables[i][r] * data.iloc[i, r] for r in range(N_ROUNDS)]
        
    # Helper variable (to allow for each member to have either three or zero rounds)
    helper = [LpVariable(f"Helper {i}", cat='Binary') for i in range(size)]

    # Create the model 
    model = LpProblem(name="LAPATOS", sense=LpMaximize)
    model += lpSum(objective_function)

    # Add the constraints
    for i in range(size):
        # Each member can only have three or zero rounds
        model += (sum([variables[i][r] for r in range(N_ROUNDS)]) == 3 * helper[i], "three_rounds_" + str(i))
    for r in range(N_ROUNDS):
        # Each round can only have five members
        model += (sum([variables[i][r] for i in range(size)]) == 5, "five_members_" + str(r))

    model.solve()

    # Print information on the model if verbose argument given
    if verbose:
        print(model)
        print(f"Status: {model.status}, {LpStatus[model.status]}")
        print(f"Objective: {model.objective.value()}")

    selection = {}
    for var in model.variables():
        if 'Helper' not in var.name:
            # Get member name and round data from variable name
            # (variables are in the form "First_Last|Round")
            s = var.name
            name = s[:s.find('|')].replace('_', ' ')
            round = int(s[s.find('|') + 1:])

            # Update the selection sheet
            if name not in selection:
                selection[name] = ['-' for _ in range(N_ROUNDS)]
            if var.value() == 1:
                selection[name][round - 1] = 'X'
    
    # Map the round number to the given round topic
    mapping = dict((i, data.columns[i]) for i in range(N_ROUNDS))

    # Convert selection to a DataFrame
    df = pd.DataFrame(selection)

    # Make some manipulations to the DataFrame
    df['Name'] = df.index
    df = df.T
    df.columns = df.iloc[len(df) - 1]
    df = df[:-1]
    df.rename(columns=mapping, inplace=True)

    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--i') # input filepath
    parser.add_argument('--o') # output filepath
    parser.add_argument('-c', action='store_true') # clear, default is false
    parser.add_argument('-v', action='store_true') # verbose, default is false
    args = parser.parse_args()
    
    selection = main(args)
    print(selection)
    
    selection.to_csv(args.o if args.o else DEFAULT_OUTPUT_FILE)