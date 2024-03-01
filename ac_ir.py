#!/usr/bin/env python3
import sys
import base64

quiet=False

def build_command(on=True,
     hvac_mode="heat",# heat, dry, cold, auto
     temperature=23, # Celcius
     fanspeedmode="fanauto", # fanauto, fanset, vaneauto, vanemove
     fanspeedset=1,
     hour=0,
     minutes=0,
     endclock_hour=0,
     endclock_minutes=0,
     startclock_hour=0,
     startclock_minutes=0,
     startclock=0,
     progmode="noprog"): #enablestart, enableend, enableendstart, noprog

    data = [0 for _ in range(18)]
    data[0] = 0x23
    data[1] = 0xCB
    data[2] = 0x26
    data[3] = 0x01
    data[4] = 0x00

    if on:
        data[5] = 0x20
    else:
        data[5] = 0x00

    if hvac_mode=="heat":
        data[6] = 0x08
        data[8] = 0x30
    elif hvac_mode=="dry":
        data[6] = 0x10
        data[8] = 0x32
    elif hvac_mode=="cold":
        data[6] = 0x18
        data[8] = 0x36
    elif hvac_mode=="auto":
        data[6] = 0x20
        data[8] = 0x30
    else:
        print("Error: hvac_mode must be one of heat, dry, cold or auto",file=sys.stderr)

    if temperature < 16 or temperature > 31:
        print("Error: temperature must be between 16C and 31C",file=sys.stderr)
    temp = temperature-16
    data[7] = temp

    if fanspeedmode == "fanauto":
        data[9] = 0x80
    elif fanspeedmode == "vaneset":
        data[9] = (fanspeedset << 3) & 0x7f
    elif fanspeedmode == "vaneauto":
        data[9] = 0x40
    elif fanspeedmode == "vanemove":
        data[9] = 0x78
    else:
        print("Error: fanspeedmode must be one of fanauto, vanesetm vaneauto or vanemove",file=sys.stderr)


    time = (6*hour)+(minutes//15)
    data[10] = time

    time = (6*endclock_hour)+(endclock_minutes//15)
    data[11] = time

    time = (6*startclock_hour)+(startclock_minutes//15)
    data[12] = time

    if progmode=="enablestart":
        data[13] = 0x05
    elif progmode=="enablend":
        data[13] = 0x03
    elif progmode=="enablendstart":
        data[13] = 0x07
    elif progmode=="noprog":
        data[13] = 0x00

    data[14]=0x00
    data[15]=0x00
    data[16]=0x00

    checksum = sum(data) % 256
    data[17]=checksum

    return data

def bigendian_bits(x):
    bits = list()
    for i in range(8):
        bits.append((x >> (7-i)) & 0x1)
    return bits

def pulse_train(data):
    pulses = list()

    header_mark  = 3400
    header_space = 1750
    bit_mark     = 450
    one_space    = 1300
    zero_space   = 420
    rpt_mark     = 440
    rpt_space    = 17100

    pulses.append(header_mark)
    pulses.append(header_space)

    for i in range(18):
        x = bigendian_bits(data[i])
        for bit in x:
            if bit == 0:
                pulses.append(bit_mark)
                pulses.append(zero_space)
            else:
                pulses.append(bit_mark)
                pulses.append(one_space)

    pulses.append(rpt_mark)
    pulses.append(rpt_space)

    pulses.append(header_mark)
    pulses.append(header_space)

    for i in range(18):
        x = bigendian_bits(data[i])
        for bit in x:
            if bit == 0:
                pulses.append(bit_mark)
                pulses.append(zero_space)
            else:
                pulses.append(bit_mark)
                pulses.append(one_space)
    return pulses


def set_heat_temp_c(temp):
    command = build_command(on=True,
        hvac_mode="heat",# heat, dry, cold, auto
        temperature=temp) # Celcius
    return(command)

def make_b64(command):
    b64_data = bytearray()
    pulses = pulse_train(command)

    pulse_length = len(pulses)
    index = 0
    if not quiet:
        print("Pulse Train Data",file=sys.stderr)
    while index < len(pulses):
        if (pulse_length-index) > 16:
            b = 31
            b64_data.append(b) # Length byte
            if not quiet:
                print("%02x," % 31 ,end="",file=sys.stderr)
            for i in range(16):
                lowbyte = pulses[index+i] & 0xff
                highbyte = (pulses[index] >> 8) & 0xff
                b64_data.append(lowbyte)
                b64_data.append(highbyte)
                if not quiet:
                    print("%02x,%02x," % (lowbyte,highbyte),end="",file=sys.stderr)
            index += 16
            if not quiet:
                print(file=sys.stderr)

        else:
            remaining_length = ((pulse_length-index)*2) & 0x1f
            b64_data.append(remaining_length-1) # length byte
            if not quiet:
                print("%02x," % (remaining_length-1),end="",file=sys.stderr)
            for i in range(pulse_length-index):
                lowbyte = pulses[index+i] & 0xff
                highbyte = (pulses[index+i] >> 8) & 0xff
                b64_data.append(lowbyte)
                b64_data.append(highbyte)
                if not quiet:
                    if i == (pulse_length-index-1):
                        print("%02x,%02x" % (lowbyte,highbyte),end="",file=sys.stderr)
                    else:
                        print("%02x,%02x," % (lowbyte,highbyte),end="",file=sys.stderr)

            index += pulse_length-index
            if not quiet:
                print(file=sys.stderr)

    return base64.b64encode(b64_data)


command = set_heat_temp_c(23)
print("Encoded Data")
thebytes = ["%02x" % x for x in command]
print(','.join(thebytes))
irstring = make_b64(command)

print(irstring)
