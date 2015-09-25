from PIL import ImageGrab, Image
import win32gui
import win32api
import win32con
import numpy as np
import time
import sys


class MCInterop:
    def __init__(self):
        # try:
        chardata = []
        for char in self.split_image(np.array(Image.open("ocrmap.png").convert("F"))):
            chardata.append(str(char))
        self.ocrmap = dict(zip(chardata, list("1234567890/.-")))
        # except:
        #    raise Exception("There was a problem with the OCR map. Make sure ocrmap.png exists in the working directory.")
        try:
            wlist = []
            toplist = []

            def enum_cb(hwnd, results):
                wlist.append((hwnd, win32gui.GetWindowText(hwnd)))

            win32gui.EnumWindows(enum_cb, toplist)
            self.handle = (hwnd for hwnd, title in wlist if title.startswith("Minecraft")).next()
        except:
            raise Exception("Couldn't get a handle for Minecraft. Check if it's open and into a world.")
        self.last_pic = None
        self.player_x = None
        self.player_y = None
        self.player_z = None
        self.player_facing_lr = None
        self.player_facing_ud = None
        self.scale = 1.0

    def grab_uncropped(self):
        bbox = win32gui.GetWindowRect(self.handle)
        return ImageGrab.grab(map((lambda x: int(x * self.scale)), bbox))

    def grab(self):
        img = self.grab_uncropped()
        cropbox = (8, 31, (img.size[0] - 8), (img.size[1] - 8))
        cropped = img.crop(cropbox)
        return cropped

    def mouse_coords(self, gx, gy):
        x, y = win32gui.GetWindowRect(self.handle)[:2]
        x += 8
        y += 31
        x += gx
        y += gy
        win32api.SetCursorPos((x, y))

    def better_sendkeys(self, kstr):
        for key in kstr:
            if key == "/":
                self.send_extended_key(0xBF, 0.05)
            elif key == " ":
                self.keypress(win32con.VK_SPACE)
            elif key == "\n":
                self.send_extended_key(0x0D, 0.05)
            elif key in list("abcdefghijklmnopqrstuvwxyz"):
                code = 0x41
                code += list("abcdefghijklmnopqrstuvwxyz").index(key)
                self.keypress(code)
            else:
                code = 0x30
                code += list("0123456789").index(key)
                self.keypress(code)
            time.sleep(0.025)

    def keypress(self, key):
        win32api.keybd_event(key, 0, 0, 0)

    def keydown(self, key):
        win32api.keybd_event(key, 0, win32con.KEYEVENTF_EXTENDEDKEY | 0, 0)

    def keyup(self, key):
        win32api.keybd_event(key, 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)

    def send_extended_key(self, key, sleep=None):
        self.keydown(key)
        if sleep:
            time.sleep(sleep)
        self.keyup(key)

    def crop_to_white(self, arr):
        nans = (arr != 255)
        nancols = np.all(nans, axis=0)
        nanrows = np.all(nans, axis=1)
        firstcol = nancols.argmin()
        firstrow = nanrows.argmin()
        lastcol = len(nancols) - nancols[::-1].argmin()
        lastrow = len(nanrows) - nanrows[::-1].argmin()
        arr = arr[firstrow:lastrow, firstcol:lastcol]
        return arr

    def scale_array(self, char_array, factor):
        target = np.zeros((char_array.shape[0] / factor, char_array.shape[1] / factor))
        for x in xrange(0, char_array.shape[0] - 1, factor):
            for y in xrange(0, char_array.shape[1] - 1, factor):
                target[x / factor, y / factor] = char_array[x, y]
        return target

    def split_image(self, text_array):
        char = []
        for i in xrange(text_array.shape[1]):
            slice = text_array[:, i]
            split = True
            for pix in slice:
                if pix == 255:
                    split = False
                    break
            if split and char:
                npr = np.rot90(np.array(char))[::-1]
                if not str(npr) == str(np.zeros(npr.shape)):
                    yield self.crop_to_white(npr)
                char = []
            else:
                char.append(list(slice))
        npr = np.rot90(np.array(char))[::-1]
        if not str(npr) == str(np.zeros(npr.shape)):
            yield self.crop_to_white(npr)

    def run_ocr(self, char):
        try:
            return self.ocrmap[str(char)]
        except:
            return ""

    def axe_damaged(self):
        return self.last_pic.getpixel((int(294 * self.scale), int(468 * self.scale))) == (232, 23, 0)

    def pick_damaged(self):
        return self.last_pic.getpixel((int(334 * self.scale), int(468 * self.scale))) == (232, 23, 0)

    def escape(self):
        self.send_extended_key(0x1B, 0.1)

    def mousedown(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)

    def mouseup(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def click(self):
        self.mousedown()
        self.mouseup()

    def rightclick(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def force_update(self):
        updated = False
        for q in xrange(3):
            print q
            self.keydown(win32con.VK_SHIFT)
            self.send_extended_key(0x44, 0.05)
            self.keyup(win32con.VK_SHIFT)
            for i in xrange(5):
                try:
                    self.update()
                    updated = True
                    break
                except:
                    pass
            if updated:
                break
        if not updated:
            raise Exception("Couldn't get an update... :(")

    def patch_hole(self):
        self.send_extended_key(win32con.VK_SPACE, 0.01)
        time.sleep(0.25)
        self.rightclick()

    def move_to(self, axis, value, comparator, shift=True, autojump=True, update=None, key=0x57, settop=None):
        if shift:
            self.keydown(0x10)  # shift
        if axis != "y":
            self.keydown(key)  # W
        try:
            self.update()
        except:
            pass
        starting_y = settop if settop else self.player_y
        falls = 0
        oldlook = None
        while True:
            try:
                self.update()
            except:
                self.force_update()
            if update:
                update()
            if axis != "y" and autojump and self.player_y < starting_y:
                if self.player_y < (starting_y - 1.5):
                    print "Fell in a hole, trying to stack up..."
                    oy = self.player_y
                    self.better_sendkeys("5")
                    if oldlook is None:
                        oldlook = self.player_facing_ud
                    self.move_look(self.player_facing_lr, 90.0, ignore_fail=True)
                    self.patch_hole()
                    self.update()
                    if self.player_y == (starting_y - 1.0):
                        self.better_sendkeys("2")
                        self.move_look(self.player_facing_lr, oldlook, ignore_fail=True)
                        oldlook = None
                        print ":)"
                    elif self.player_y == oy:
                        raise Exception("Fell in a hole... :(")
                else:
                    print "Fell in a hole, jumping out."
                    self.send_extended_key(0x20, 0.1)  # jump (space)
                    falls += 1
                    if falls >= 8:
                        self.move_look(self.player_facing_lr, 90.0, ignore_fail=True)
                        self.patch_hole()
                        self.move_look(self.player_facing_lr, 0.0, ignore_fail=True)
                        falls = 0
            else:
                falls = 0
            if axis == "x":
                if comparator == "lt":
                    if self.player_x <= value:
                        self.keyup(key)
                        break
                elif comparator == "gt":
                    if self.player_x >= value:
                        self.keyup(key)
                        break
            elif axis == "y":
                if comparator == "lt":
                    if self.player_y <= value:
                        break
                elif comparator == "gt":
                    if self.player_y >= value:
                        break
            elif axis == "z":
                if comparator == "lt":
                    if self.player_z <= value:
                        self.keyup(key)
                        break
                elif comparator == "gt":
                    if self.player_z >= value:
                        self.keyup(key)
                        break
        if shift:
            self.keyup(0x10)

    def move_look(self, lr, ud, ignore_fail=False):
        try:
            self.update()
        except:
            self.force_update()
        correct_factor = 0.10
        corrections = 0
        while abs(self.player_facing_lr - lr) > correct_factor or abs(self.player_facing_ud - ud) > correct_factor:
            try:
                self.update()
                if abs(self.player_facing_lr - lr) > 100:
                    lr_factor = 64
                elif abs(self.player_facing_lr - lr) > 50:
                    lr_factor = 48
                elif abs(self.player_facing_lr - lr) > 25:
                    lr_factor = 25
                elif abs(self.player_facing_lr - lr) > 5:
                    lr_factor = 10
                elif abs(self.player_facing_lr - lr) > 2.5:
                    lr_factor = 4
                else:
                    lr_factor = 1
                    corrections += 0.5
                    if corrections > 20:
                        self.correct_factor += 0.1
                        corrections = 0
                if abs(self.player_facing_ud - ud) > 100:
                    ud_factor = 64
                elif abs(self.player_facing_ud - ud) > 50:
                    ud_factor = 48
                elif abs(self.player_facing_ud - ud) > 25:
                    ud_factor = 25
                elif abs(self.player_facing_ud - ud) > 5:
                    ud_factor = 10
                elif abs(self.player_facing_ud - ud) > 2.5:
                    ud_factor = 4
                else:
                    ud_factor = 1
                    corrections += 0.5
                    if corrections > 20:
                        self.correct_factor += 0.1
                        corrections = 0
                x = 0
                if abs(self.player_facing_lr - lr) < correct_factor:
                    x = 0
                elif (lr - self.player_facing_lr) < 0:
                    x = -lr_factor
                else:
                    x = lr_factor
                y = 0
                if abs(self.player_facing_ud - ud) < correct_factor:
                    y = 0
                elif (ud - self.player_facing_ud) < 0:
                    y = -ud_factor
                else:
                    y = ud_factor
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x, y)
                fails = 0
            except:
                if not ignore_fail:
                    self.force_update()
                else:
                    correct_factor += 0.1

    def update(self):
        self.last_pic = self.grab_uncropped()
        debug = self.last_pic.convert("F")
        self.last_pic = self.last_pic.crop(
            map(int, (8 * self.scale, 31 * self.scale, (self.last_pic.size[0] - 8), (self.last_pic.size[1] - 8))))
        # self.last_pic.show()
        # sys.exit()
        debug = np.array(
            debug.crop(map(int, (8 * self.scale, 31 * self.scale, debug.size[0] - 8, ((debug.size[1] / 3) * 2)))))
        debug[debug != 224] = 0
        debug[debug == 224] = 255
        debug = self.crop_to_white(debug)
        debug = debug[(debug.shape[0] / 2) - 10:(debug.shape[0] / 2) + 71 + 10, :550]
        debug[:12, 425:] = 0
        debug = self.crop_to_white(debug)  # [:71,:]
        # debug[19:40,291:] = 0
        coords = self.scale_array(self.crop_to_white(debug[:14, 48:]), 2)
        facing = self.scale_array(self.crop_to_white(debug[54:54 + 14, 340:]), 2)[:, 5:-5]
        # try:/warp wood
        #    if facing[1,1] != 255:
        #        facing = facing[:,6:]
        # except:
        #    pass
        # Image.fromarray(facing).show()
        try:
            coords_str = []
            for char in self.split_image(coords):
                coords_str.append(self.run_ocr(char))
            coords_str = "".join(coords_str)
            self.player_x, self.player_y, self.player_z = map(float, coords_str.split("/"))
        except:
            pass
        facing_str = []
        for char in self.split_image(facing):
            facing_str.append(self.run_ocr(char))
        facing_str = "".join(facing_str)
        # print facing_str
        self.player_facing_lr, self.player_facing_ud = map(float, facing_str.split("/"))


def deposit():
    mci.better_sendkeys("/u home")
    time.sleep(0.075)
    mci.better_sendkeys("\n")
    time.sleep(1.5)
    mci.move_look(90, 0, ignore_fail=True)
    mci.move_to("x", 24995, "lt")
    mci.move_look(-10.0, 0.0, ignore_fail=True)
    mci.move_to("z", 1406, "gt", shift=False)
    mci.move_look(0.0, 0.0, ignore_fail=True)
    mci.rightclick()
    time.sleep(0.25)
    mci.keydown(win32con.VK_SHIFT)
    for y in [260, 300, 330]:
        for x in xrange(260, 610, 35):
            mci.mouse_coords(int(x / mci.scale), int(y / mci.scale))
            mci.click()
            time.sleep(0.075)
    for x in xrange(425 + 35, 610, 35):
        mci.mouse_coords(int(x / mci.scale), int(380 / mci.scale))
        mci.click()
        time.sleep(0.075)
    mci.keyup(win32con.VK_SHIFT)
    time.sleep(0.1)
    mci.escape()
    time.sleep(0.75)


def mine_to_start_wood():
    mci.better_sendkeys("/")
    time.sleep(0.1)
    mci.better_sendkeys("warp wo")
    time.sleep(0.1)
    mci.better_sendkeys("od")
    time.sleep(0.5)
    mci.better_sendkeys("\n")
    time.sleep(2)
    mci.keyup(0x57)
    mci.move_to("z", -660, "lt", shift=False, autojump=False)
    mci.update()
    while mci.player_y > 661.0:
        mci.send_extended_key(0x53, 0.075)  # S
        mci.update()
    mci.move_look(90.0, -90.0, ignore_fail=True)
    mci.move_to("x", -73, "lt", shift=False, autojump=False)
    time.sleep(1.5)
    mci.move_to("x", -110, "lt", shift=False, settop=59.000)
    mci.update()
    while mci.player_y > 59.0:
        mci.send_extended_key(0x53, 0.05)  # S
        mci.update()
    mci.move_look(0.0, -90.0, ignore_fail=True)

    def move_update():
        if mci.player_x < -109.600:
            mci.send_extended_key(0x41, 0.04)  # A

    mci.move_to("z", -610, "gt", shift=False, update=move_update)
    mci.move_to("z", -608.700, "gt", shift=False, autojump=False, update=move_update)
    # mci.send_extended_key(0x57, 0.15)
    # mci.keydown(win32con.VK_SHIFT)
    mci.update()
    print "doing stuff"
    while mci.player_y > 59.0:
        mci.send_extended_key(0x53, 0.05)  # S
        mci.update()
    while mci.player_x >= -109.300:
        mci.send_extended_key(0x44, 0.05)  # D
        mci.update()
    while mci.player_x <= -109.700:
        mci.send_extended_key(0x41, 0.05)  # A
        mci.update()
    while mci.player_z <= -608.600:
        print "moo"
        mci.send_extended_key(0x57, 0.05)  # W
        mci.update()
    print "done doing stuff"
    # mci.keyup(win32con.VK_SHIFT)
    time.sleep(1)
    mci.update()
    if mci.player_y > 50.0:
        mci.move_look(45.0, 90.0, ignore_fail=True)
        mci.better_sendkeys("2")
        # mci.send_extended_key(0x57, 0.05)  # W
        # time.sleep(0.01)
        # mci.send_extended_key(0x44, 0.15)  # D
        mci.update()
        while mci.player_y > 59.0:
            mci.send_extended_key(0x41, 0.03)  # A
            mci.update()
        time.sleep(2)
        mci.update()
        mci.mousedown()
        mci.move_to("y", 50, "lt", shift=False)
        mci.mouseup()
    if mci.player_y < 50.0:
        oldlook = mci.player_facing_ud
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 65535)
        while mci.player_y < 50.0:
            mci.patch_hole()
            time.sleep(0.25)
            mci.update()
            mci.move_look(mci.player_facing_lr, oldlook, ignore_fail=True)
    time.sleep(0.5)


def mine_channel_wood():
    mci.move_look(-179.0, 30, ignore_fail=True)

    def path_align():
        if mci.player_x > -109.400:
            mci.send_extended_key(0x41, 0.04)
        return mci.axe_damaged() and mci.player_y != 59.000  # no resets

    mci.send_extended_key(0x57, 1.0)
    mci.update()
    if mci.player_z < -608.701:
        print "already done"
    else:
        mci.mousedown()
        mci.move_to("z", -702, "lt", shift=False, update=path_align)
        mci.mouseup()
        if mci.axe_damaged() or mci.player_y == 59.000:
            return


time.sleep(2)
start = time.time()
grabs = 0.0
mci = MCInterop()
mci.update()
while not mci.axe_damaged():
    mine_to_start_wood()
    mine_channel_wood()
    deposit()
sys.exit()
