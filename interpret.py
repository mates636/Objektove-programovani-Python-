#jméno a příjmení: Martin Priessnitz
#login: xpries01


import re
import argparse
import xml.etree.ElementTree as ET
from sys import stderr, stdin, exit

#vnitřní reprezentace načteného zdrojového kódu
#konstruktor vyžaduje kořenový element zdrojové XML struktury
#obsahuje jedinou proměnnou self.ins, což je seznam instrukcí programu. -instance třídy Instruction
#Provadí nezbytný preprocesing např.: kontrolu orderu a seřazení atd.
#parsování vnitřních XML elemntu deleguje na třídu Instruction

class Program:
    def __init__(self, xmlRoot):
        if xmlRoot.attrib.get('language').lower() != 'IPPcode23'.lower():
            stderr.write("wrong header")
            exit(32)
        if xmlRoot.tag != 'program':
            stderr.write("missing program")
            exit(32)
        self.ins = []
        for instruction in xmlRoot:
            self.ins.append(Instruction(instruction))
        self.ins = sorted(self.ins, key = lambda x:x.order)
        for i in range(len(self.ins )-1):
            if self.ins[i].order == self.ins[i+1].order:
                stderr.write("duplikatni order")
                exit(32)

#reprezentuje jednu instrukci ze zdrojového kódu
#ověřuje a načítá atributy elementu instruction 
#parsování vnitřních elemntů deleguje na třídu Argument
#obsahuje self.order, opcode a arg, což je seznam argumentů(instance třídy Argument)
class Instruction:
    #všechny možné typy instrukcí
    opcodes = ['MOVE', 'CREATEFRAME', 'PUSHFRAME', 'POPFRAME', 'DEFVAR', 'CALL', 
               'RETURN', 'PUSHS', 'POPS', 'ADD', 'SUB', 'MUL', 'IDIV', 'LT', 'GT', 
               'EQ', 'AND', 'OR', 'NOT', 'INT2CHAR', 'STRI2INT', 'READ', 'WRITE', 
               'CONCAT', 'STRLEN', 'GETCHAR', 'SETCHAR', 'TYPE', 'LABEL', 'JUMP', 
               'JUMPIFEQ', 'JUMPIFNEQ', 'EXIT', 'DPRINT', 'BREAK']
    def __init__(self, xml):
        try:
            self.order = int(xml.attrib.get('order'))
        except Exception as e:
            stderr.write("wrong order {}".format(e))
            exit(32)
        if xml.tag != "instruction":
            stderr.write("chybi instruction")
            exit(32)
        if self.order <= 0:
            stderr.write("negative order {}".format(self.order))
            exit(32)
        self.opcode = xml.attrib.get('opcode', "").upper()
        if not self.opcode in self.opcodes:
            stderr.write("wrong instruction {}".format(self.opcode))
            exit(32)
        self.arg = []
        for argument in xml:
            self.arg.append(Argument(argument))
        self.arg = sorted(self.arg, key = lambda x:x.argNum)
        i = 1
        for arg in self.arg:
            if arg.argNum != i:
                stderr.write("wrong sorted argNum")
                exit(32)
            i+=1


class Argument:
    types = ['var', 'label', 'int', 'bool', 'string', 'type', 'nil']
    def __init__(self, xml):
        if not xml.tag.startswith('arg'):
            stderr.write("not start with arg")
            exit(32)
        try:
            self.argNum = int(xml.tag[3:])
        except Exception as e:
            stderr.write("wrong arg number {}".format(e))
            exit(32)
        if not self.argNum in [1,2,3]:
            stderr.write("wrong arg number 2: {}\n".format(self.argNum))
            exit(32)
        try:
            self.type = xml.attrib.get('type')
        except Exception as e:
            stderr.write("missing type {}".format(e))
            exit(32)
        if not self.type in self.types:
            stderr.write("wrong type {}".format(self.type))
            exit(32)
        self.name = xml.text
        

    
#reprezentuje jeden frame v paměti
#proměnné si ukládá formou slovníku, kde klíč je název proměnné a hodnota je hodnota proměnné
class Frame:
    def __init__(self):
        self.vars = dict()
    #funkce pro získání proměnné
    def get(self, name):
        return self.vars[name]
    #funkce pro definici promněnné
    def defVar(self,name):
        if name in self.vars:
            stderr.write("already existing variable {}".format(name))
            exit(52)
        self.vars[name] = None
    #funkce pro změnu hodnoty proměnné
    def set(self, name, value):
        if name not in self.vars:
            stderr.write("setting non existing variable {}".format(name))
            exit(54)
        self.vars[name] = value
    #funkce, která zjišťuje existenci proměnné
    def exists(self, name):
        return name in self.vars
#reprezentuje paměťový model programu 
#spolu s instancí třídy Interpret jednoznačně určuje aktuální stav výpočtu 
#obsahuje všechny framy(GF, TF a zásobník LF)
class Memory:
    def __init__(self):
        self.globalFrame = Frame()
        self.temporaryFrame = None
        self.localFrames = []
        self.callStack = []
        self.dataStack = []
    #funkce pro získání proměnné
    def get(self, varName):
        name = varName.split("@")
        frame = name[0]
        try:
            if frame == "GF":
                return self.globalFrame.get(name[1])
            elif frame == "TF":
                return self.temporaryFrame.get(name[1])
            elif frame == "LF":
                return self.localFrames[-1].get(name[1])
            else:
                stderr.write("wrong frame {}".format(name[0]))
                exit(54)
        except Exception as e:
            stderr.write("undefined frame {}".format(e))
            exit(55)
    #funkce pro změnu hodnoty proměnné
    def set(self, varName, value):
        name = varName.split("@")
        frame = name[0]
        try:
            if frame == "GF":
                return self.globalFrame.set(name[1], value)
            elif frame == "TF":
                return self.temporaryFrame.set(name[1], value)
            elif frame == "LF":
                return self.localFrames[-1].set(name[1], value)
            else:
                stderr.write("wrong frame {}".format(name[0]))
                exit(54)
        except Exception as e:
            stderr.write("undefined frame {}".format(e))
            exit(55)
    #funkce pro definici promněnné
    def defVar(self, varName):
        name = varName.split("@")
        frame = name[0]
        try:
            if frame == "GF":
                return self.globalFrame.defVar(name[1])
            elif frame == "TF":
                return self.temporaryFrame.defVar(name[1])
            elif frame == "LF":
                return self.localFrames[-1].defVar(name[1])
            else:
                stderr.write("wrong frame {}".format(name[0]))
                exit(54)
        except Exception as e:
            stderr.write("undefined frame {}".format(e))
            exit(55)
            
#top-level třída: definuje vnější rozhraní interpretu 
#v konstruktoru projde program a načte všechna návěští 
#interpretace programu se spouští skrz funkci run()
class Interpret:
    def __init__(self, program, inputFile):
        self.program = program
        self.pc = 1
        self.memory = Memory()
        self.inputFile = inputFile
        self.labels = dict()
        for i in range(len(program.ins)):
            if program.ins[i].opcode == "LABEL":
                if len(program.ins[i].arg) != 1:
                    stderr.write("spatny pocet arg11 {}".format(program.ins[i].arg))
                    exit(32)
                if program.ins[i].arg[0].type != "label":
                    stderr.write("spatny typ arg")
                    exit(53)
                if program.ins[i].arg[0].name in self.labels:
                    stderr.write("stejne pojmenovani navesti")
                    exit(52)
                self.labels[program.ins[i].arg[0].name] = i+1
    def run(self):
        while(True):
            if self.pc == len(self.program.ins) + 1:
                break
            self.runInstruction()
    #funkce, která posílá na jednotlivé funkce programu
    def runInstruction(self):
        ins = self.program.ins[self.pc - 1]
        if ins.opcode == "MOVE":
            self.move(ins)
        if ins.opcode == "CREATEFRAME":
            self.createFrame(ins)
        if ins.opcode == "PUSHFRAME":
            self.pushFrame(ins)
        if ins.opcode == "POPFRAME":
            self.popFrame(ins)
        if ins.opcode == "DEFVAR":
            self.defVar(ins)
        if ins.opcode == "CALL":
            self.call(ins)
        if ins.opcode == "RETURN":
            self.returnn(ins)
        if ins.opcode == "PUSHS":
            self.pushs(ins)
        if ins.opcode == "POPS":
            self.pops(ins)
        if ins.opcode == "ADD":
            self.add(ins)
        if ins.opcode == "SUB":
            self.sub(ins)
        if ins.opcode == "MUL":
            self.mul(ins)
        if ins.opcode == "IDIV":
            self.idiv(ins)
        if ins.opcode == "LT":
            self.lt(ins)
        if ins.opcode == "GT":
            self.gt(ins)
        if ins.opcode == "EQ":
            self.eq(ins)
        if ins.opcode == "AND":
            self.andd(ins)
        if ins.opcode == "OR":
            self.orr(ins)
        if ins.opcode == "NOT":
            self.nott(ins)
        if ins.opcode == "INT2CHAR":
            self.int2char(ins)
        if ins.opcode == "STRI2INT":
            self.stri2int(ins)
        if ins.opcode == "READ":
            self.read(ins)
        if ins.opcode == "WRITE":
            self.write(ins)
        if ins.opcode == "CONCAT":
            self.concat(ins)
        if ins.opcode == "STRLEN":
            self.strlen(ins)
        if ins.opcode == "GETCHAR":
            self.getchar(ins)
        if ins.opcode == "SETCHAR":
            self.setchar(ins)
        if ins.opcode == "TYPE":
            self.typee(ins)
        if ins.opcode == "LABEL":
            self.label(ins)
        if ins.opcode == "JUMP":
            self.jump(ins)
        if ins.opcode == "JUMPIFEQ":
            self.jumpifeq(ins)
        if ins.opcode == "JUMPIFNEQ":
            self.jumpifneq(ins)
        if ins.opcode == "EXIT":
            self.eexit(ins)
        if ins.opcode == "DPRINT":
            self.dprint(ins)
        if ins.opcode == "BREAK":
            self.breakk(ins)

#definice funkci
    def move(self, ins):
        if len(ins.arg) != 2:
            stderr.write("spatny pocet arg11 {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type != "var":
            if ins.arg[1].type == "int":
                symVal = int(ins.arg[1].name)
            elif ins.arg[1].type == "string":
                symVal = str(ins.arg[1].name)
            elif ins.arg[1].type == "bool":
                if ins.arg[1].name.lower() == 'true':
                    symVal = True
                else:
                    symVal = False
            elif ins.arg[1].type == "nil":
                symVal = None
        if ins.arg[1].type == "var":
            symVal = self.memory.get(ins.arg[1].name)
        self.memory.set(ins.arg[0].name, symVal)
        self.pc+=1
    def createFrame(self, ins):
        if len(ins.arg) != 0:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        self.memory.temporaryFrame = Frame()
        self.pc+=1
    def pushFrame(self, ins):
        if self.memory.temporaryFrame == None:
            stderr.write("nemam TF")
            exit(55)
        self.memory.localFrames.append(self.memory.temporaryFrame)
        self.memory.temporaryFrame = None
        self.pc+=1
    def popFrame(self, ins):
        if self.memory.localFrames == []:
            stderr.write("nemam LF")
            exit(55)
        self.memory.temporaryFrame = self.memory.localFrames[-1]
        self.memory.localFrames.pop()
        self.pc+=1
    def defVar(self, ins):
        if len(ins.arg) != 1:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        self.memory.defVar(ins.arg[0].name)
        self.pc+=1
    def call(self, ins):
        if len(ins.arg) != 1:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "label":
            stderr.write("spatny typ argumentu")
            exit(53)
        self.memory.callStack.append(self.pc+1)
        if ins.arg[0].name not in self.labels:
            stderr.write("neznamy label")
            exit(52)
        self.pc = self.labels[ins.arg[0].name]
    def returnn(self, ins):
        if self.memory.callStack == []:
            stderr.write("prazdny list")
            exit(56)
        self.pc = self.memory.callStack.pop()
    def pushs(self, ins):
        if len(ins.arg) != 1:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type == "var":
            var1 = self.memory.get(ins.arg[0].name)
        else:
            var1 = getValue(ins.arg[0])
        self.memory.dataStack.append(var1)
        self.pc+=1
    def pops(self, ins):
        if len(ins.arg) != 1:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if self.memory.dataStack == []:
            stderr.write("prazdny zasobnik")
            exit(56)
        value = self.memory.dataStack.pop()
        self.memory.set(ins.arg[0].name, value)
        self.pc+=1

    #aritmeticke, relacni, booleovske a konverzni instrukce
    
    def add(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != int or type(var2) != int:
            stderr.write("spatny typ")
            exit(53)
        result = var1 + var2
        self.memory.set(ins.arg[0].name, result)
        self.pc += 1
    def sub(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != int or type(var2) != int:
            stderr.write("spatny typ")
            exit(53)
        result = var1 - var2
        self.memory.set(ins.arg[0].name, result)
        self.pc += 1
    def mul(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != int or type(var2) != int:
            stderr.write("spatny typ")
            exit(53)
        result = var1 * var2
        self.memory.set(ins.arg[0].name, result)
        self.pc += 1
    def idiv(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != int or type(var2) != int:
            stderr.write("spatny typ")
            exit(53)
        if var2 == 0:
            stderr.write("deleni nulou")
            exit(57)
        result = int(var1 / var2)
        self.memory.set(ins.arg[0].name, result)
        self.pc += 1
    def lt(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) == str and type(var2) == str:
            if var1 < var2:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        elif type(var1) == int and type(var2) == int:
            if var1 < var2:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        elif type(var1) == bool and type(var2) == bool:
            if var1 == False and var2 == True:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        else:
            stderr.write("spatne operandy")
            exit(53)
        self.pc+=1
    def gt(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) == str and type(var2) == str:
            if var1 > var2:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        elif type(var1) == int and type(var2) == int:
            if var1 > var2:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        elif type(var1) == bool and type(var2) == bool:
            if var1 == True and var2 == False:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        else:
            stderr.write("spatne operandy")
            exit(53)
        self.pc+=1
    def eq(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) == str and type(var2) == str:
            if var1 == var2:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        elif type(var1) == int and type(var2) == int:
            if var1 == var2:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        elif type(var1) == bool and type(var2) == bool:
            if var1 == False and var2 == False or var1 == True and var2 == True:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        elif var1 == None or var2 == None:
            if var1 == var2:
                self.memory.set(ins.arg[0].name, True)
            else:
                self.memory.set(ins.arg[0].name, False)
        else:
            stderr.write("spatne operandy")
            exit(53)
        self.pc+=1
    def andd(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny operand")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != bool or type(var2) != bool:
            stderr.write("spatny typ")
            exit(53)
        self.memory.set(ins.arg[0].name, var1 and var2)
        self.pc+=1
    def orr(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny operand")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != bool or type(var2) != bool:
            stderr.write("spatny typ")
            exit(53)
        self.memory.set(ins.arg[0].name, var1 or var2)
        self.pc+=1
    def nott(self, ins):
        if len(ins.arg) != 2:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny operand")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if type(var1) != bool:
            stderr.write("spatny typ")
            exit(53)
        self.memory.set(ins.arg[0].name, not var1)
        self.pc+=1
    def int2char(self, ins):
        if len(ins.arg) != 2:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny operand")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if type(var1) != int:
            stderr.write("spatny typ")
            exit(53)
        try:
            char = chr(int(var1))
            self.memory.set(ins.arg[0].name, char)
            self.pc+=1
        except Exception as e:
            stderr.write("spatna ordinalni hodnota")
            exit(58)
    def stri2int(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny operand")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var2) != int:
            stderr.write("spatny typ")
            exit(53)
        if type(var1) != str:
            stderr.write("spatny typ")
            exit(53)
        index = var2
        if index >= 0 and index <= len(var1):
            var2 = ord(var1[index])
            self.memory.set(ins.arg[0].name, var2)
            self.pc+=1
        else:
            stderr.write("spatna delka")
            exit(58)
        
    def read(self, ins):
        if len(ins.arg) != 2:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var" or ins.arg[1].type != "type":
            stderr.write("spatne operandy {}, {}".format(ins.arg[0].type, ins.arg[1].type))
            exit(32)
        rawValue = self.inputFile.readline().rstrip('\n')
        try:
            if rawValue == "":
                value = None
            elif ins.arg[1].name == "int":
                value = int(rawValue)
            elif ins.arg[1].name == "bool":
                if rawValue.lower() == 'true':
                    value = True
                else:
                    value = False
            elif ins.arg[1].name == "string":
                value = rawValue
            elif ins.arg[1].name == "nil":
                value = None
            else:
                stderr.write("unknow type {}".format(value))
                exit(52)
        except Exception as e:
            value = None
        self.memory.set(ins.arg[0].name, value)
        self.pc+=1
    def write(self, ins):
        if len(ins.arg) != 1:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type == "var":
            value = self.memory.get(ins.arg[0].name)
            if value == None:
                value = ""
            elif type(value) == bool:
                if value == True:
                    value = "true"
                else:
                    value = "false"
        elif ins.arg[0].type == "bool":
            if ins.arg[0].name == "true":
                value = "true"
            else:
                value = "false"
        elif ins.arg[0].type == "int":
            value = ins.arg[0].name
        elif ins.arg[0].type == "string":
            value = ins.arg[0].name
        elif ins.arg[0].type == "nil":
            value = ""
        else:
            stderr.write("spatny typ operandu")
            exit(53)
        def replace(match):
            return int(match.group(1)).to_bytes(1, byteorder="big")
        if type(value) == str:
            value = bytes(value, "UTF-8")
            regex = re.compile(rb"\\(\d{1,3})")
            value = regex.sub(replace, value).decode()
        print(value , end = "")
        self.pc+=1
    def concat(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
            if type(var1) != str:
                stderr.write("neni string")
                exit(53)
        elif ins.arg[1].type == "string":
            var1 = ins.arg[1].name
        else:
            stderr.write("spatny argument")
            exit(53)
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)

            if type(var2) != str:
                stderr.write("neni string")
                exit(53)
        elif ins.arg[2].type == "string":
            var2 = ins.arg[2].name
        else:
            stderr.write("spatny argument")
            exit(53)
        concat = (var1 + var2)
        self.memory.set(ins.arg[0].name, concat)
        self.pc+=1
    def strlen(self, ins):
        if len(ins.arg) != 2:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if type(var1) != str:
            stderr.write("neni string")
            exit(53)
        varLen = len(var1)
        self.memory.set(ins.arg[0].name, varLen)
        self.pc+=1
    def getchar(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != str or type(var2) != int:
            stderr.write("spatne typy")
            exit(53)
        var1Len = len(var1)
        symbVal = var2
        if var1Len <= symbVal or symbVal < 0:
            stderr.write("hodnota vetsi jak retezec")
            exit(58)
        self.memory.set(ins.arg[0].name, var1[var2])
        self.pc+=1
    def setchar(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != int or type(var2) != str:
            stderr.write("spatne typy")
            exit(53)
        var = self.memory.get(ins.arg[0].name)
        if len(var) <= var1 or var1 < 0 or len(var2) == 0:
            stderr.write("hodnota vetsi jak retezec")
            exit(58)
        text = var
        new = list(text)
        new[var1] = var2[0]
        var = ''.join(new)
        self.memory.set(ins.arg[0].name, var)
        self.pc+=1
    def typee(self, ins):
        if len(ins.arg) != 2:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "var":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if var1 == None:
            typ = "nil"
            self.memory.set(ins.arg[0].name, typ)
            self.pc+=1  
        elif type(var1) == str:
            typ ="string"
            self.memory.set(ins.arg[0].name, typ)
            self.pc+=1
        elif type(var1) == bool:
            typ = "bool"
            self.memory.set(ins.arg[0].name, typ)
            self.pc+=1
        elif type(var1) == int:
            typ = "int"
            self.memory.set(ins.arg[0].name, typ)
            self.pc+=1
        else:
            stderr.write("spatny operand")
            exit(53)
    def label(self, ins):
        self.pc+=1
    def jump(self, ins):
        if len(ins.arg) != 1:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "label":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[0].name not in self.labels:
            stderr.write("neznamy label")
            exit(52)
        self.pc = self.labels[ins.arg[0].name]
    def jumpifeq(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "label":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[0].name not in self.labels:
            stderr.write("neznamy label")
            exit(52)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != type(var2) and var1 != None and var2 != None:
            stderr.write("spatne typy")
            exit(53)
        if var1 == var2:
            self.pc = self.labels[ins.arg[0].name]
        else:
            self.pc+=1
    def jumpifneq(self, ins):
        if len(ins.arg) != 3:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type != "label":
            stderr.write("spatny typ argumentu")
            exit(53)
        if ins.arg[0].name not in self.labels:
            stderr.write("neznamy label")
            exit(52)
        if ins.arg[1].type == "var":
            var1 = self.memory.get(ins.arg[1].name)
        else:
            var1 = getValue(ins.arg[1])
        if ins.arg[2].type == "var":
            var2 = self.memory.get(ins.arg[2].name)
        else:
            var2 = getValue(ins.arg[2])
        if type(var1) != type(var2) and var1 != None and var2 != None:
            stderr.write("spatne typy")
            exit(53)
        if var1 != var2:
            self.pc = self.labels[ins.arg[0].name]
        else:
            self.pc+=1
    def eexit(self, ins):
        if len(ins.arg) != 1:
            stderr.write("spatny pocet arg {}".format(ins.arg))
            exit(32)
        if ins.arg[0].type == "var":
            var = self.memory.get(ins.arg[0].name)
        else:
            var = getValue(ins.arg[0])
        if type(var) != int:
            stderr.write("spatny typ")
            exit(53)
        if var >= 0 and var <= 49:
            exit(var)
        else:
            stderr.write("spatny int")
            exit(57)
        self.pc+=1
    def dprint(self, ins):
        self.pc+=1
    def breakk(self, ins):
        self.pc+=1

#pomocná funkce vrací hodnotu argumentu konstantního symbolu
def getValue(arg):
    if arg.type == "int":
        symVal = int(arg.name)
    elif arg.type == "string":
        symVal = str(arg.name)
    elif arg.type == "bool":
        if arg.name.lower() == 'true':
            symVal = True
        else:
            symVal = False
    elif arg.type == "nil":
        symVal = None
    else:
        stderr.write("spatny typ")
        exit(53)
    return symVal


sourceFile = ""
inputFile = ""

parser = argparse.ArgumentParser(add_help = False)
parser.add_argument("--help", action = "store_true")
parser.add_argument("--source")
parser.add_argument("--input")
args = parser.parse_args()

if args.help:
    print("--help:")
    print("--source=file pro vstupní soubor s XML reprezentací zdrojového kódu")
    print("--input=file soubor se vstupy pro samotnou interpretaci zadaného zdrojového kódu")
    if args.source or args.input:
        exit(10)
    else:
        exit(0)
try:
    if args.source:
        with open(args.source, "r") as fp:
            tree = ET.parse(fp)
    else:
        tree = ET.parse(stdin)
    vals = []
    root = tree.getroot()
    program = Program(tree.getroot())
except Exception as e:
    stderr.write(str(e)+"\n")
    stderr.write("missing source file")
    exit(31)
try:
    if args.input:
        inputFile = open(args.input, "r")
    else:
        inputFile = stdin
except Exception as e:
    stderr.write("missing input file")
    exit(31)
interpreter = Interpret(program, inputFile)
interpreter.run()




