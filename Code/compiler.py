"""
GAPlus - GAP Parallel Compiler using OpenCL
By Bar Bokovza

This is the compiler python file
It get's list of GAP rule, analyse it and return python code to run.
The code that are retrieved are in python, but the CL functions are the OpenCL functions that runs underneath
"""
__author__ = "Bar Bokovza"

# noinspection PyPep8

#region IMPORTS
import numpy as np

from Code.dataHolder import GAP_Data

#endregion

#region ENUMS
class BlockType(object):
    """ Presents the type of block from shape atom(args):notation """
    UNKNOWN = 0
    ANNOTATION = 1
    ABOVE = 2

class RuleType(object):
    """
    presents the type of GAP rule
    """
    UNKNOWN = 0
    HEADER = 1
    GROUND = 2
    COMPLEX = 3

#endregion

#region p_ Functions

def _IsFloat (number):
    # noinspection PyBroadException
    try:
        float(number)
    except Exception:
        return False
    return True

def _IsEmpty (array):
    """
    Return true if the array is empty
    :param array: an array
    :return: True / False
    :rtype: bool
    """
    return np.shape(array)[0] == 0

def _Parse_Block (block):
    """
    Gets a block in a GAP Rule and return a tuple of (atom, args, notation, blockType)
    :param block: block in a GAP rule
    :return: (atom:str, args:list, notation:str, blockType:BlockType)
    :rtype: tuple
    :raise ValueError: The predicat [predicat] does not have an atom and arguments
    """
    predicat, notation = block.split(":")

    atoms = predicat.split(",")
    if len(atoms) < 2:
        raise ValueError("The predicat '" + predicat + "' does not have an atom and arguments")

    atom, args = atoms[0], atoms[1:]

    return atom, args, notation

def _Parse_Rule (rule):
    """
    gets a string of rule, and return a tuple with header, body and a list of args that are avaliable in the rule
    :param rule: GAP Rule in string
    :type rule: str
    :return: simplified header, simplified items in body, and list of arguments that are in the rule.
    :rtype: tuple
    """
    args = []

    rule = rule.replace(" ", "")
    rule = rule.replace("(", ",")
    rule = rule.replace(")", "")
    rule = rule.replace("[", ",")
    rule = rule.replace("]", "")
    str_header, str_body = rule.split("<-")

    headerBlock = _Parse_Block(str_header)
    args.append(headerBlock[1])

    body_lst = []

    for block in str_body.split("&"):
        parsedBlock = _Parse_Block(block)
        body_lst.append(parsedBlock)
        args.append(parsedBlock[1])

    return headerBlock, body_lst, args

def _Create_VirtualVarsPic (arguments, dictionary):
    """
    transform arg variables from names to numbers
    :param arguments: list of arguments of a block
    :param dictionary: dictionary of arguments
    :return: the list of arguments in numbers instead of names
    """
    virtual = []

    for arg in arguments:
        virtual.append(dictionary[arg])

    return virtual

def _Create_PhysicalVarsPic (virtual, size):
    """
    transform virtual pic to physical pic
    :param virtual: the virtual variables picture
    :param size: the amount of unique arguments in rule
    :return:physical variables picture of the virtual that we got as a parameter
    """
    result = np.zeros(size, dtype = np.int32)
    result.fill(-1)

    count = 0
    matches = []

    for ptr in virtual:
        if result[ptr] == -1:
            result[ptr] = count
            count += 1
        else:
            matches.append((result[ptr], count))

    return result, matches

def _Create_ArgumentsDictionary (lst):
    """
    create dictionary of arguments variables based on the list of args that we get from parameter
    :param lst: list of arguments variables in names
    :type lst:list
    :return: dictionary of that list
    """
    result = { }
    count = 0

    for args in lst:
        for arg in args:
            if not arg in result:
                result[arg] = count
                count += 1

    return result

def _Create_CommandString (lst):
    """
    Create a string of a list code
    :param lst: list code (build from tuples of (str, number)
    :type lst: list
    :return: string of a code with tabs
    :rtype: str
    """
    result = ""

    for line in lst:
        text, tabsCount = line

        command = ""
        for i in range(tabsCount):
            command += "\t"

        command += text
        result += command + "\n"

    return result

#endregion

#region Definition Zone Private Functions
# The number presents the amount of tabs before

def DefZone_Create_Dictionaries (lst, addon = 0):
    """
    create python code for the dictionaries
    :param lst: list of predicats in the rules
    :type lst:list
    :param addon: how many tabs to add to the command
    :type addon:int
    :return: python commands in list and amount of tabs needed
    :rtype: list
    """
    result = []

    for predicat in lst:
        result.append(("dict_{0}=MainDict[\"{0}\"]".format(predicat), addon))
        result.append(("array_{0} = dataHold.Generate_NDArray(\"{0}\")".format(predicat), addon))

    return result

# endregion

# region GAP Block
class GAP_Block:
    """
    This is the class of GAP Block
    it analyses GAP block and save all the needed data for it.
    """

    def __init__ (self, parsed, dictionary = None):
        """
        Initialization
        :param parsed: basic tuple of a block
        :param dictionary: the dictionary of the arguments variables in a rule.
        """
        predicat, arguments, notation = parsed
        self.Predicat, self.Notation = predicat, notation

        self.Notation = self.Notation.replace("\n", "")
        self.Notation = self.Notation.replace("\r", "")

        self.Type = BlockType.ANNOTATION
        if _IsFloat(self.Notation):
            self.Type = BlockType.ABOVE

        self.VirtualVarsPic = _Create_VirtualVarsPic(arguments, dictionary)
        size = len(dictionary)
        self.PhysicalVarsPic, self.Matches = _Create_PhysicalVarsPic(self.VirtualVarsPic, size)

    def Bool_NeedFilter (self):
        """
        return true if the arguments in the block needs to pass Filtering
        :return: boolean value
        :rtype: bool
        """
        return not len(self.Matches) is 0

    def __str__ (self):
        result = self.Predicat + " ("
        for num in self.VirtualVarsPic:
            result += int(num).__str__() + " "

        result += "): " + self.Notation
        return result

    def __repr__ (self):
        return self.__str__()

    def p_cmp (self, other):
        """
        compare function
        :param other: the other object to compare to
        :return: how much the objects are different
        """
        if self.Type is not other.Type:
            return self.Type - other.Type

        if len(self.Matches) is not len(other.Matches):
            return len(self.Matches) - len(other.Matches)

        if len(self.VirtualVarsPic) is not len(other.VirtualVarsPic):
            return len(self.VirtualVarsPic) - len(other.VirtualVarsPic)

        return 0

    def __eq__ (self, other):
        return self.p_cmp(other) is 0

    def __ge__ (self, other):
        return self.p_cmp(other) >= 0

    def __gt__ (self, other):
        return self.p_cmp(other) > 0

    def __le__ (self, other):
        return self.p_cmp(other) <= 0

    def __lt__ (self, other):
        return self.p_cmp(other) < 0

#endregion

#region GAP Rule
class GAP_Rule:
    """
    it analyses and save all the data needed for a single gap rule.
    """

    def __init__ (self, rule):
        """
        Initialization
        :param rule: GAP Rule in string
        :type rule: str
        """
        headerBlock, bodyBlock, args = _Parse_Rule(rule)
        self.Dictionary = _Create_ArgumentsDictionary(args)
        self.Body, self.Predicats = [], []
        self.Header = GAP_Block(headerBlock, self.Dictionary)
        self.Type = RuleType.HEADER

        self.Code_Run, self.Predicats_Dependent = [], []

        self.Predicats.append(headerBlock[0])

        for block in bodyBlock:
            parsed_block = GAP_Block(block, self.Dictionary)

            if parsed_block.Type == BlockType.ANNOTATION and self.Type == RuleType.HEADER:
                self.Type = RuleType.GROUND
            elif parsed_block.Type == BlockType.ABOVE:
                self.Type = RuleType.COMPLEX

            self.Body.append(parsed_block)

            if block[0] not in self.Predicats:
                self.Predicats.append(block[0])

            if block[0] not in self.Predicats_Dependent:
                self.Predicats_Dependent.append(block[0])

        self.Body.sort()

        if self.Type == RuleType.HEADER:
            self.Predicats_Dependent = [headerBlock[0]]

    def __str__ (self):
        result = ""

        result = result + self.Header.__str__() + " <- "
        for i in range(0, len(self.Body) - 1):
            result = result + self.Body[i].__str__()
            if i + 1 < len(self.Body):
                result += " & "

        return result

    def __repr__ (self):
        return self.__str__()

    def Create_CompiledCode (self, total, idx = 0, addon = 0, eps = 0.00001):
        """
        Compile for the code for the running (without "Definition Zone")
        :param total: amount of arguments variables
        :type total:int
        :param idx: the index of the rule
        :type idx:int
        :param addon: how much tabs do add
        :type addon: int
        :param eps: the epsilon of the rule [default = 0.000001]
        :type eps:float
        :return: code list
        :rtype: list
        """
        result = []

        result.append(("def Rule_{0}(def_zone:tuple, lst:list, index:int):".format(idx), addon))
        result.append(("assigns, varsPic = def_zone", addon + 1))
        result.append(("added, changed = 0,0", addon + 1))

        result.append(("for row in assigns:", addon + 1))

        for i in range(total):
            result.append(("a_{0} = row[varsPic[{0}]]".format(i), addon + 2))

        for block in self.Body:
            if block.Type == BlockType.ANNOTATION:
                tupleKey = ""
                for idx in block.VirtualVarsPic:
                    tupleKey += "a_{0},".format(idx)

                result.append(
                    ("{0}=MainDict[\"{1}\"][({2})]".format(block.Notation, block.Predicat, tupleKey), addon + 2))

        block = self.Header
        tupleKey = ""
        for idx in block.VirtualVarsPic:
            tupleKey += "a_{0},".format(idx)

        result.append((
            "if ({0}) not in MainDict[\"{1}\"].keys() and {2} > 0:".format(tupleKey, block.Predicat, block.Notation),
            addon + 2))
        result.append(("added+=1", addon + 3))
        result.append(("MainDict[\"{0}\"][({1})] = {2}".format(block.Predicat, tupleKey, block.Notation), addon + 3))

        result.append((
            "elif {0} >= MainDict[\"{1}\"][({2})]+({3}):".format(block.Notation, block.Predicat, tupleKey, eps),
            addon + 2))
        result.append(("changed+=1", addon + 3))
        result.append(("MainDict[\"{0}\"][({1})] = {2}".format(block.Predicat, tupleKey, block.Notation), addon + 3))

        result.append(("lst[index] = (added, changed)", addon + 1))
        result.append(("return", addon + 1))
        return result

    def Create_CompiledCode_HeaderRule (self, total, idx = 0, addon = 0, eps = 0.00001):
        """
        Compile for the code for the running [Header rule] (without "Definition Zone")
        :param total: amount of arguments variables
        :type total:int
        :param idx: the index of the rule
        :type idx:int
        :param addon: how much tabs do add
        :type addon: int
        :param eps: the epsilon of the rule [default = 0.000001]
        :type eps:float
        :return: code list
        :rtype: list
        """
        result = []

        result.append(("def Rule_{0}(def_zone:tuple, lst:list, index:int):".format(idx), addon))
        result.append(("assigns, varsPic = def_zone", addon + 1))
        result.append(("changed = 0", addon + 1))

        result.append(("for row in assigns:", addon + 1))

        for i in range(total):
            result.append(("a_{0} = row[varsPic[{0}]]".format(i), addon + 2))

        block = self.Header
        tupleKey = ""
        for idx in block.VirtualVarsPic:
            tupleKey += "a_{0},".format(idx)

        result.append((
            "if {0} >= MainDict[\"{1}\"][({2})]+({3}):".format(block.Notation, block.Predicat, tupleKey, eps),
            addon + 2))
        result.append(("changed+=1", addon + 3))
        result.append(("MainDict[\"{0}\"][({1})] = {2}".format(block.Predicat, tupleKey, block.Notation), addon + 3))

        result.append(("lst[index] = (added, changed)", addon + 1))
        result.append(("return", addon + 1))

        return result

    def Arrange_Execution (self, idx, addon = 0):
        """
        Before execution, compile the rule
        :param idx: the index of the rule
        :type idx: int
        :param addon: how much tabs to add to the code
        :type addon: int
        """
        if self.Type == RuleType.HEADER:
            self.Code_Run = compile(_Create_CommandString(
                self.Create_CompiledCode_HeaderRule(len(self.Dictionary), idx = idx, addon = addon)), "<string>",
                "exec")
        else:
            self.Code_Run = compile(
                _Create_CommandString(self.Create_CompiledCode(len(self.Dictionary), idx = idx, addon = addon)),
                "<string>", "exec")

    def Create_DefinitionZone_Join (self, arrays, gpu):
        """
        Executing the PART B in the Definition Zone algorithm : Join
        :param arrays: The Arrays to join
        :type arrays: list
        :param gpu: the execution agent for the relational functions (OpenCL / Basic)
        :return: list of arrays with only 1 array
        :rtype: list
        """
        next = []

        while len(arrays) > 1:
            while len(arrays) > 0:
                if len(arrays) is 1:
                    next.append(arrays.pop(0))
                else:
                    a = arrays.pop(0)
                    b = arrays.pop(0)

                    res = gpu.SuperJoin(a, b)
                    if _IsEmpty(res[0]):
                        arrays.clear()
                        arrays.append(res)
                        return arrays

                    next.append(res)

            arrays = next
            next = []

        return arrays

    def Create_DefinitionZone (self, dataHolder, gpu):
        """
        Executing the fully algorithm of "Definition Zone"
        :param dataHolder: the data agent
        :type dataHolder: GAP_Data
        :param gpu: The relational functions agent (OpenCL / Basic)
        """
        lst = list(range(len(self.Body)))

        arrays = []
        aboveLst = []

        for i in lst:
            block = self.Body[i]

            if (len(block.Matches) > 0):
                array = gpu.Filter((dataHolder.Generate_NDArray(block.Predicat), block.PhysicalVarsPic), block.Matches)
            else:
                array = (dataHolder.Generate_NDArray(block.Predicat), block.PhysicalVarsPic)

            if _IsEmpty(array[0]):
                return array
            arrays.append(array)

            if block.Type is BlockType.ABOVE:
                aboveLst.append(i)

        arrays = self.Create_DefinitionZone_Join(arrays, gpu)

        final_idx, final_varsPic = arrays[0]

        if _IsEmpty(final_idx):
            return final_idx, final_varsPic

        if len(aboveLst) > 0:
            for i in aboveLst:
                block = self.Body[i]

                after = gpu.SelectAbove_Full((final_idx, final_varsPic), block.VirtualVarsPic,
                    dataHolder.GetData(block.Predicat), float(block.Notation))

                if _IsEmpty(after[0]):
                    return after

                arrays.append(after)

            arrays = self.Create_DefinitionZone_Join(arrays, gpu)
            final_idx, final_varsPic = arrays[0]
            final_idx, _vals = gpu.Distinct(final_idx)

        return final_idx, final_varsPic

#endregion

#region GAP Compiler
class GAP_Compiler:
    """
    it loads a gap file (of more than 1) and compile the rules to python code
    """

    def __init__ (self, eps = 0.00001):
        """
        Initialization
        :param eps: epsilon of the gap rules
        :type eps: float
        """
        self.Rules = []
        self.e = eps

    def Load (self, path):
        """
        load a single gap file into the compiler
        :param path: Gap file path
        :type path: str
        """
        filer = open(path, "r")

        for line in filer.readlines():
            rule = GAP_Rule(line)
            self.Rules.append(rule)

    def GetPredicats (self):
        """
        Get the predicats avaliable of all the predicats in the all rules
        :return: list of predicats
        :rtype: list
        """
        lst = []

        for rule in self.Rules:
            for atom in rule.Predicats:
                if atom not in lst:
                    lst.append(atom)

        return lst

    def PreRun (self):
        """
        Execute before Running the code on the engine
        """
        count = 0
        for rule in self.Rules:
            rule.Arrange_Execution(count)
            count += 1

    def Reset (self):
        """
        Clean all rules from the compiler
        """
        self.Rules.clear()

        #endregion