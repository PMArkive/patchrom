import sys
import os
import glob
import struct

code = '';
addrdb = {};
base = 0x00100000;

def findNearestSTMFD(code, pos):
	pos = (pos // 4) * 4;
	term = pos - 0x1000;
	if term < 0:
		term = 0;
	while (pos >= term) :
		if (code[pos + 2: pos + 4] == '\x2d\xe9'):
			return pos;
		pos -= 4;
	return 0;
	
def findFunction(code, sig):
	global base;
	
	t = code.find(sig);
	if (t == -1):
		return 0;
	return base + findNearestSTMFD(code, t);

def save(k, v):
	global addrdb, base;
	if (not addrdb.has_key(k)):
		addrdb[k] = '0';
	if (v != 0):
		addrdb[k] = hex(v);

def findAll(code, sig):
	r = [];
	off = 0;
	while True:
		t = code.find(sig, off);
		if (t == -1):
			return r;
		off = t + 1;
		r.append(t);

def parseHexStr(s):
	t = '';
	for i in s.split(' '):
		if (len(i) > 0): 
			t += chr(int('0x' + i, 0));
	return t;

def locateHid():
	global code, base;
	
	save('hidObj', 0);
	t = code.find('hid:USER');
	if (t == -1):
		print('strHidUser not found');
		return;
	strHidUser =  t + base;
	print('strHidUser: %08x' % strHidUser);
	
	t = code.find(struct.pack('I', strHidUser));
	if (t == -1):
		print('refHidUser not found');
		return;
	refHidUser =  t + base;
	print('refHidUser: %08x' % refHidUser);
	
	r = findAll(code, struct.pack('I', refHidUser - 8));
	hidObj = 0;
	for i in r:
		(t,) = struct.unpack('I', code[i + 4: i + 8]);	
		if ((t & 0x80000000) == 0):
			hidObj = t;

	print('hidObj: %08x' % hidObj);
	
	save('hidObj', hidObj);

def locateFS() :
	global code, base;
	save('fsUserHandle', 0);
	save('fsOpenFile', findFunction(code, parseHexStr('c2 01 02 08')));
	save('fsOpenArchive', findFunction(code, parseHexStr('c2 00 0c 08')));
	save('fsWriteFile', findFunction(code, parseHexStr('02 01 03 08')));
	t = code.find(parseHexStr('f9 67 a0 08'));
	if (t == 0):
		return;
	(fsUserHandle,) = struct.unpack('I', code[t - 4: t]);
	save('fsUserHandle', fsUserHandle);

def findFreeSpace():
	off = textSize - 8;
	while True:
		(t,) = struct.unpack('I', code[off: off + 4]);
		if (t != 0):
			break;
		off -= 4;
	off += 8;
	save('freeStart', off + base);
	save('freeSize', textSize - off - 4);
	save('freeBss', textBase + textSize + roSize + rwSize + bssSize);
	save('freeBssSize', 0x4000);
	


with open("../workdir/exh.bin", "rb") as f:
	exh = f.read(64);

(textBase, textPages, roPages, rwPages, bssSize) =struct.unpack(
'16xii4x4x4xi4x4x4xi4xi', exh);
textSize = textPages * 0x1000;
roSize = roPages * 0x1000;
rwSize = rwPages * 0x1000;
bssSize = ( (bssSize / 0x1000) + 1 ) * 0x1000;
save('textSize', textSize);
save('roSize', roSize);
save('rwSize', rwSize);
save('bssSize', bssSize);
save('base', base);


with open('../workdir/exefs/code.bin', 'rb') as f:
	code = f.read();


save('mountRom', findFunction(code, parseHexStr('0C 00 9D E5 00 10 90 E5  28 10 91 E5 31 FF 2F E1  ')));
save('mountRom', findFunction(code, '\x31\xFF\x2F\xE1\x04\x00\xA0\xE1\x0F\x10\xA0\xE1\xA4\x2F\xB0\xE1'));
save('mountArchive', findFunction(code, '\x10\x00\x97\xE5\xD8\x20\xCD\xE1\x00\x00\x8D'));
save('regArchive', findFunction(code, '\xB4\x44\x20\xC8\x59\x46\x60\xD8'));
save('mountArchive', findFunction(code, '\x28\xD0\x4D\xE2\x00\x40\xA0\xE1\xA8\x60\x9F\xE5\x01\xC0\xA0\xE3'));
save('getServiceHandle', findFunction(code, parseHexStr(' F8 67 A0 D8')));


locateHid();
locateFS();
findFreeSpace();

print(repr(addrdb));

for i in addrdb:
	if (addrdb[i] == 0):
		print('***WARNING*** Failed locating symbol %s , some patches may not work.' % i); 

with open('../workdir/exefs/symbols.txt', 'w') as f:
	f.write(repr(addrdb));