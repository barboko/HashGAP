__author__ = "Bar Bokovza"

from enum import Enum
import copy

import numpy as np

import validation


class BlockType( Enum ):
    UNKNOWN_BLOCK = 0
    ANNOTATION_BLOCK = 1
    ABOVE_BLOCK = 2

class RuleType( Enum ):
    ONCE_HEADER_RULE = 1
    ONCE_GROUND_RULE = 2
    HEADER_RULE = 3
    BASIC_RULE = 4
    COMPLEX_RULE = 5

def create_varsPic_matches ( args, varsDict ) -> tuple:  # (result, matches, count)
    matches = []
    size = len( varsDict.keys( ) )
    result = np.zeros( size, dtype = np.int32 )

    for i in range( 0, size ):
        result [i] = -1

    count = 0
    for arg in args:
        if not arg in varsDict.keys( ):
            raise ValueError( "The wrong dictionary have been sent to the function." )

        idx = varsDict [arg]

        if result [idx] == -1:
            result [idx] = count
        else:
            matches.append( (result [idx], count) )

        count = count + 1

    return result, matches, count


def parse ( rules ) -> list:  # (headerBlock, body_lst)
    result = []
    for rule in rules:
        rule = rule.replace( " ", "" )
        rule = rule.replace( "(", "," )
        rule = rule.replace( ")", "" )
        rule = rule.replace( "[", "," )
        rule = rule.replace( "]", "" )
        str_header, str_body = rule.split( "<-" )

        headerBlock = parse_block( str_header )
        if headerBlock [3] != BlockType.ANNOTATION_BLOCK:
            raise ValueError( "In Header the block must be an annotation block." )

        body_lst = []

        for block in str_body.split( "&" ):
            parsedBlock = parse_block( block )
            body_lst.append( parsedBlock )

        result.append( (headerBlock, body_lst) )

    return result


def parse_block ( block ) -> (str, list, str, BlockType):
    """
    Gets a block in a GAP Rule and return a tuple of (atom, args, notation, blockType)
    :param block:
    :return: tuple => (atom:str, args:list, notation:str, blockType:BlockType)
    :raise ValueError:
    """
    predicat, notation = block.split( ":" )
    blockType = BlockType.UNKNOWN_BLOCK
    if validation.v_IsFloat( notation ):
        blockType = BlockType.ABOVE_BLOCK
    else:
        blockType = BlockType.ANNOTATION_BLOCK

    atoms = predicat.split( "," )
    if len( atoms ) < 2:
        raise ValueError( "The predicat '" + predicat + "' does not have an atom and arguments" )

    atom, args = atoms [0], atoms [1:]

    return atom, args, notation, blockType

def analyse_rule ( rule ):
    arg_dict = {}
    predicats = []
    count = 0

    headerBlock, bodyBlocks = rule

    blockLst = copy.deepcopy( bodyBlocks )
    blockLst.append( headerBlock )

    finalLst = []

    for block in blockLst:
        atom, args, notation, type = block
        if not atom in predicats:
            predicats.append( atom )
        for arg in args:
            if not arg in arg_dict:
                arg_dict [arg] = count
                count = count + 1

    for block in blockLst:
        atom, args, notation, type = block
        varPic, matches, count = create_varsPic_matches( args, arg_dict )
        finalLst.append( (atom, args, notation, type, varPic, matches, count) )

    headerRes = finalLst [len( finalLst ) - 1]
    bodyRes = finalLst [0:len( finalLst ) - 2]

    bodyRes.sort( key = lambda item: item [6] )

    return (headerRes, bodyRes)

def cmp_bodyBlock ( a, b ) -> int:
    a_varPic, b_varPic = a [4], b [4]
    a_count, b_count = 0, 0

    for item in a_varPic:
        if item != -1:
            a_count = a_count + 1

    for item in b_varPic:
        if item != -1:
            b_count = a_count + 1

    if a_count > b_count:
        return -1
    if a_count < b_count:
        return 1
    return 0


class GAP_Compiler:
    rules = []

    def __int__ ( self ):
        rules = []

    def load ( self, path ):
        lines = []
        filer = open( path, "r" )

        for line in filer.readline( ):
            lines.append( line )

        result = parse( lines )

        for item in result:
            self.rules.append( item )


