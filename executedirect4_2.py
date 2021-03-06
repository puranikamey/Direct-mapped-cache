#! python
# (c) DL, UTA, 2009 - 2016
import  sys, string, time,pprint
wordsize = 24                                        # everything is a word
numregbits = 3                                       # actually +1, msb is indirect bit
opcodesize = 5
addrsize = wordsize - (opcodesize+numregbits+1)      # num bits in address
memloadsize = 1024                                   # change this for larger programs
numregs = 2**numregbits
regmask = (numregs*2)-1                              # including indirect bit
addmask = (2**(wordsize - addrsize)) -1
nummask = (2**(wordsize))-1
opcposition = wordsize - (opcodesize + 1)            # shift value to position opcode
reg1position = opcposition - (numregbits +1)            # first register position
reg2position = reg1position - (numregbits +1)
memaddrimmedposition = reg2position                  # mem address or immediate same place as reg2
realmemsize = memloadsize * 1                        # this is memory size, should be (much) bigger than a program
cache= [['-2-2-2-2-2-2-2-2' for i in range(3)] for j in range(4)] # cache data structure 
#variables declared
hits=0
misses=0
complmiss=0
conflit=0
#memory management regs
codeseg = numregs - 1                                # last reg is a code segment pointer
dataseg = numregs - 2                                # next to last reg is a data segment pointer
#ints and traps
trapreglink = numregs - 3                            # store return value here
trapval     = numregs - 4                            # pass which trap/int
mem = [0] * realmemsize                              # this is memory, init to 0 
reg = [0] * numregs                                  # registers
clock = 1                                            # clock starts ticking
ic = 0                                               # instruction count
eic = 0
numcoderefs = 0                                      # number of times instructions read
numdatarefs = 0                                      # number of times data read
starttime = time.time()
curtime = starttime
def startexechere ( p ):
    # start execution at this address
    reg[ codeseg ] = p    
def loadmem():                                       # get binary load image
  curaddr = 0
  for line in open("a.out", 'r').readlines():
    token = string.split( string.lower( line ))      # first token on each line is mem word, ignore rest
    if ( token[ 0 ] == 'go' ):
        startexechere(  int( token[ 1 ] ) )
    else:    
        mem[ curaddr ] = int( token[ 0 ], 0 )                
        curaddr = curaddr = curaddr + 1
#function to handle instruction cache for cat program 
def cachesearch(a):
    global cache
    global hits
    global misses
    global complmiss
    global conflit
    binary = '{0:08b}'.format(a)
    offset =int ( binary[-1], 2)
    index =int ( binary [-3:-1], 2) 
    if str(cache[index][2]) == str(binary[:-3]) and str(cache[index][offset]) != '-2-2-2-2-2-2-2-2':
      hits +=1
      return (cache[index][offset])
    else: 
      misses +=1
      length=0
      for x in cache :
       length +=len(set(x))
       if length==4:
          complmiss +=1
       elif cache[index][offset] != '-2-2-2-2-2-2-2-2':
           conflit +=1
      cache[index][offset] = getcodemem(a)
      cache[index][2] = binary[:-3]
      if offset==0 :
         cache[index][1] = getcodemem(a+1)
      else :
         cache[index][0]= getcodemem(a-1)
      return (cache[index][offset])
#function to handle data  instruction sets of the cache.
def datasearch(a):
    global cache
    global hits
    global misses
    global complmiss
    global conflit
    binary = '{0:08b}'.format(a)
    offset =int ( binary[-1], 2)
    index =int ( binary [-3:-1], 2) 
    if str(cache[index][2]) == str(binary[:-3]) and str(cache[index][offset]) != '-2-2-2-2-2-2-2-2':
      hits +=1
      return (cache[index][offset])
    else: 
      misses +=1
      length=0
      for x in cache :
       length +=len(set(x))
       if length==4:
          complmiss +=1
      cache[index][offset] = getdatamem(a)
      cache[index][2] = binary[:-3]
      if offset==0 :
         cache[index][offset] = getdatamem(a+1)
      else :
         cache[index][offset-1]= getdatamem(a-1)
      return (cache[index][offset])

def getcodemem ( a ):
    # get code memory at this address
    memval = mem[ a + reg[ codeseg ] ]
    return ( memval )
def getdatamem ( a ):
    # get code memory at this address
    global numdatarefs
    numdatarefs += 1
    memval = mem[ a + reg[ dataseg ] ]
    return ( memval )
def getregval ( r ):
    # get reg or indirect value
    if ( (r & (1<<numregbits)) == 0 ):               # not indirect
       rval = reg[ r ] 
    else:
      rval = datasearch(reg[ r - numregs ])
      # rval = getdatamem( reg[ r - numregs ] )       # indirect data with mem address
    return ( rval )
def checkres( v1, v2, res):
    #print "v1: ", v1
    #print "v2: ", v2
    #print "res: ", res
    v1sign = ( v1 >> (wordsize - 1) ) & 1
    v2sign = ( v2 >> (wordsize - 1) ) & 1
    ressign = ( res >> (wordsize - 1) ) & 1
    if ( ( v1sign ) & ( v2sign ) & ( not ressign ) ):
      return ( 1 )
    elif ( ( not v1sign ) & ( not v2sign ) & ( ressign ) ):
      return ( 1 )
    else:
      return( 0 )
def dumpstate ( d ):
    if ( d == 1 ):
        print reg
    elif ( d == 2 ):
        print mem
    elif ( d == 3 ):
        print 'clock=', clock, 'IC=', ic, 'Coderefs=', numcoderefs,'Datarefs=', numdatarefs, 'Start Time=', starttime, 'Currently=', time.time(), "executed=", eic 
    elif (d==4) :
        pprint.pprint(cache)
        print'this is the miss counted '
        pprint.pprint(misses)
        print 'this is the hit counted'
        pprint.pprint(hits)
        print 'this is the compulsory miss counted'
        pprint.pprint(complmiss)
        print 'this is the conflict miss counted'
        pprint.pprint(conflit)
        
def trap ( t ):
    # unusual cases
    # trap 0 illegal instruction
    # trap 1 arithmetic overflow
    # trap 2 sys call
    # trap 3+ user
    rl = trapreglink                            # store return value here
    rv = trapval
    if ( ( t == 0 ) | ( t == 1 ) ):
       dumpstate( 1 )
       dumpstate( 2 )
       dumpstate( 3 )
       dumpstate( 4 )
    elif ( t == 2 ):                          # sys call, reg trapval has a parameter
       what = reg[ trapval ] 
       if ( what == 1 ):
           a = a        #elapsed time
    return ( -1, -1 )
    return ( rv, rl )
# opcode type (1 reg, 2 reg, reg+addr, immed), mnemonic  
opcodes = { 1: (2, 'add'), 2: ( 2, 'sub'), 
            3: (1, 'dec'), 4: ( 1, 'inc' ),
            7: (3, 'ld'),  8: (3, 'st'), 9: (3, 'ldi'),
           12: (3, 'bnz'), 13: (3, 'brl'),
           14: (1, 'ret'),
           16: (3, 'int') }
startexechere( 0 )                                  # start execution here if no "go"
loadmem()                                           # load binary executable
ip = 0                                              # start execution at codeseg location 0
# while instruction is not halt
while( 1 ):
   ir = cachesearch(ip)
   ir= int(ir)
   #ir = getcodemem( ip )                            # - fetch
   ip = ip + 1
   opcode = ir >> opcposition                       # - decode
   reg1   = (ir >> reg1position) & regmask
   #print "reg1:", reg1
   reg2   = (ir >> reg2position) & regmask
   addr   = (ir) & addmask
   ic = ic + 1
                                                    # - operand fetch
   if not (opcodes.has_key( opcode )):
      tval, treg = trap(0) 
      if (tval == -1):                              # illegal instruction
         break
   memdata = 0                                      #     contents of memory for loads
   if opcodes[ opcode ] [0] == 1:                   #     dec, inc, ret type
      operand1 = getregval( reg1 )                  #       fetch operands
   elif opcodes[ opcode ] [0] == 2:                 #     add, sub type
      operand1 = getregval( reg1 )                  #       fetch operands
      operand2 = getregval( reg2 )
   elif opcodes[ opcode ] [0] == 3:                 #     ld, st, br type
      operand1 = getregval( reg1 )                  #       fetch operands
      operand2 = addr                     
   elif opcodes[ opcode ] [0] == 0:                 #     ? type
      break
   if (opcode == 7):                                # get data memory for loads
      memdata = datasearch(operand2) 
    #getdatamem( operand2 )

   operand1 = int(operand1)
   operand2 = int(operand2)
   # execute
   numcoderefs += 1
   if opcode == 1:                     # add
      result = (operand1 + operand2) & nummask
      if ( checkres( operand1, operand2, result )):
         tval, treg = trap(1) 
         if (tval == -1):                           # overflow
            break
   elif opcode == 2:                   # sub
      result = (operand1 - operand2) & nummask
      if ( checkres( operand1, operand2, result )):
         tval, treg = trap(1) 
         if (tval == -1):                           # overflow
            break
   elif opcode == 3:                   # dec
      result = operand1 - 1
   elif opcode == 4:                   # inc
      result = operand1 + 1
   elif opcode == 7:                   # load
      result = memdata
   elif opcode == 9:                   # load immediate
      result = operand2
   elif opcode == 12:                  # conditional branch
      result = operand1
      if result <> 0:
         ip = operand2
   elif opcode == 13:                  # branch and link
      result = ip
      ip = operand2
   elif opcode == 14:                   # return
      ip = operand1
   elif opcode == 16:                   # interrupt/sys call
      result = ip
      tval, treg = trap(reg1)
      if (tval == -1):
        break
      reg1 = treg
      ip = operand2
   # write back
   if ( (opcode == 1) | (opcode == 2 ) | 
         (opcode == 3) | (opcode == 4 ) ):     # arithmetic
        reg[ reg1 ] = result
   elif ( (opcode == 7) | (opcode == 9 )):     # loads
        reg[ reg1 ] = result
   elif (opcode == 13):                        # store return address
        reg[ reg1 ] = result
   elif (opcode == 16):                        # store return address
        reg[ reg1 ] = result
   # end of instruction loop     
# end of execution

   
