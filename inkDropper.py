# coding:utf-8
"""
Copyright (c) 2018 iCyP
Released under the MIT license
https://opensource.org/licenses/mit-license.php

"""

import PIL.Image
import PIL.ImageTk
import tkinter
import tkinter.filedialog
from collections import deque
import heapq
import numpy
import sys
import os
import datetime

devmode = False

# 以下にアルゴリズムを実装する。
# 大 TODO  :階調を255からfloatなどに変えたい：openEXR等を検討？


class Pixel():
    def __init__(self, cost: int, pos: (int, int)):
        self.cost = cost
        self.pos = numpy.array(pos)
    # heapqのため

    def __lt__(self, other):
        return self.cost < other.cost
    # なんとなく

    def __eq__(self, other):
        return self.pos == other.pos


class Island():
    def __init__(self, island_id):
        self.positions = []
        self.island_id = island_id
        self.visited = False


def fill_islandID_and_make_island(start_points: [], island_map: numpy.ndarray, islandID: int):
    width = island_map.shape[0]
    height = island_map.shape[1]

    island = Island(islandID)
    search_queue = deque(start_points)
    for pos in start_points:
        island_map[pos[0]][pos[1]] = islandID

    while search_queue:
        pos = search_queue.pop()
        for dirction in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            x = int(pos[0]+dirction[0])
            y = int(pos[1]+dirction[1])
            if x < 0 or y < 0 or x >= width or y >= height:
                continue
            if island_map[x, y] == 0:
                island_map[x, y] = islandID
                island.positions.append((x, y))
                search_queue.append((x, y))
    return island

# ↓ 言うほど遅くない


def islands_mapping(P_image: PIL.Image, startPoints: []):
    # とりあえず全部未探索(0)埋め地図作成
    island_map = numpy.zeros(shape=(P_image.width, P_image.height), dtype=int)
    island_id = 1  # -1:海 0:未探索 1~:島ID
    height_range = range(P_image.height)  # 都度生成よりこの方が早い？
    width_range = range(P_image.width)
    # 島と海を分ける
    for y in height_range:
        for x in width_range:
            if P_image.getpixel((x, y))[0] <= 125:  # 赤が125以下なら海とする
                island_map[x, y] = -1
    # 島を番号づける、島のﾘｽﾄを作る
    island_dict = {}
    island_dict[-1] = Island(-1)  # 海も一種の島として扱う
    # 第一の島は複数選択されている可能性があるのですべて1島としてセットする。
    # TODO 開始地点が海だった時の処理（なくても動いてるけど・・・(たぶん1島がバグってるはずだけど、島IDで処理分けしない限り大丈夫)
    island = fill_islandID_and_make_island(startPoints, island_map, island_id)
    island_dict[island.island_id] = island
    # 島探索
    for y in height_range:
        for x in width_range:
            if island_map[x, y] == 0:
                island_id += 1
                island_dict[island_id] = fill_islandID_and_make_island(
                    [(x, y)], island_map, island_id)

    return island_map, island_id, island_dict  # 地図と最大IDと島辞書も返す

# ↓ ☆いーなんかっわ善改どけ！いーそっおゃちっめ


def mapping(priority_heapq: [], cost_map, island_map: numpy.ndarray, island_dict):
    max_cost = 0
    min_cost = numpy.iinfo(numpy.int32).max
    width = island_map.shape[0]
    height = island_map.shape[1]
    while priority_heapq:
        basePix = heapq.heappop(priority_heapq)
        new_cost = basePix.cost+1
        for dirction in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            search_pos = (int(basePix.pos[0]+dirction[0]),
                          int(basePix.pos[1]+dirction[1]))
            # 突き抜け防止
            if search_pos[0] < 0 or search_pos[1] < 0 or search_pos[0] >= width or search_pos[1] >= height:
                continue
            # 海(-1)からきてvisitedな島なら上陸しない。
            if island_map[basePix.pos[0]][basePix.pos[1]] == -1 and island_dict[island_map[search_pos[0]][search_pos[1]]].visited:
                continue
            if cost_map[search_pos[0]][search_pos[1]] > new_cost:
                # 地図を更新して優先度付きキューに突っ込む
                cost_map[search_pos[0]][search_pos[1]] = new_cost
                heapq.heappush(priority_heapq, Pixel(new_cost, search_pos))
                # 島にいる場合、来たフラグを立てる
                if island_map[search_pos[0]][search_pos[1]] != -1:
                    island_dict[island_map[search_pos[0]]
                                [search_pos[1]]].visited = True
                    # ついでに海じゃないので最大・最小コストを更新 #海は入れられないのでnumpy.max,minは使えない
                    if max_cost < new_cost:
                        max_cost = new_cost
                    if min_cost > new_cost:
                        min_cost = new_cost
    return max_cost, min_cost


def execute(P_image: PIL.Image, startPositions: [])->PIL.Image:
    maximum_cost = 9999999
    fillHeapq = []
    for pos in startPositions:
        heapq.heappush(fillHeapq, Pixel(1, pos))
    cost_map = numpy.full(shape=(P_image.width, P_image.height),
                          dtype=int, fill_value=maximum_cost)
    # 現状max_island_IDはデバッグ用の値
    island_map, max_island_ID, island_dict = islands_mapping(P_image,
                                                             startPositions)

    # """探索
    now = datetime.datetime.now()
    max_cost, min_cost = mapping(fillHeapq, cost_map, island_map, island_dict)
    print("search :" + str(datetime.datetime.now()-now))
    # """

    # """画像に書き込む
    i_height = P_image.height  # この方が早いらしい？
    i_width = P_image.width

    image_new_array = numpy.array(P_image)
    if max_cost == 0:
        max_cost = 1  # ないだろうけど魔除け
    for x in range(i_width):
        for y in range(i_height):
            color = image_new_array[y, x]  # ndarrayは変換時、[高さ][幅][色]で持つのでxy逆転する
            if cost_map[x, y] < maximum_cost and color[0] > 0:
                # 255段階に正規化。出来ればfloatとかで出したいけど・・・
                c = int(255*(cost_map[x, y]-min_cost)/max_cost)
                color[0] = c
                color[1] = c
                color[2] = c
    P_image = PIL.Image.fromarray(image_new_array, "RGB")

    # """
    # 島ごとに色分け デバッグ用。
    """
    hsv_img = PIL.Image.new("HSV",(image.width,image.height),(255,255,255))
    for y in range(image.height):
        for x in range(image.width):
            v = 255 if island_map[x,y] != -1 else 0
            hsv_img.putpixel((x,y),(int(island_map[x,y]/max_island_ID*255),255,v))
    image = hsv_img.convert("RGB")
    #"""
    if devmode:
        P_image.show()

    return P_image


# ---------UIセクション--------------
# コールバックで参照消えるから保持させるために置く
global img
# UIかくのきらい
# TODO 多点開始対応


def main():
    root = tkinter.Tk()
    frame = tkinter.Frame(root, width=500, height=500)
    frame.pack(expand=True, fill=tkinter.BOTH)
    canvas = tkinter.Canvas(frame, width=500, height=500,
                            scrollregion=(0, 0, 1000, 1000))
    N, S, W, E = tkinter.N, tkinter.S, tkinter.W, tkinter.E
    canvas.grid(row=0, column=0, sticky=N+E+W+S)
    hbar = tkinter.Scrollbar(
        frame, orient=tkinter.HORIZONTAL, command=canvas.xview)
    hbar.grid(row=1, column=0, sticky=E+W)
    vbar = tkinter.Scrollbar(
        frame, orient=tkinter.VERTICAL, command=canvas.yview)
    vbar.grid(row=0, column=1, sticky=N+S)
    canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
    frame.grid_rowconfigure(0, weight=1, minsize=0)
    frame.grid_columnconfigure(0, weight=1, minsize=0)

    # 基本はユーザーディレクトリを開く
    init_dir = os.path.expanduser('~\\')
    if devmode:  # 面倒くさいので相対パスで適当な素材を開く。
        PIL_Img = PIL.Image.open('./sozai/65079724_p0.png')
    else:
        img_file_path = tkinter.filedialog.askopenfilename(
            filetypes=[("画像", "*")], initialdir=init_dir)
        init_dir = os.path.dirname(img_file_path)
        PIL_Img = PIL.Image.open(img_file_path)
    PIL_Img = PIL_Img.convert("RGB")  # ２値だったりアルファ付きで配列長変わるからこれを正規化とする
    img = PIL.ImageTk.PhotoImage(PIL_Img)
    max_canvas_size = 512  # あんまりでかいと邪魔だから適当な最大サイズを設定
    wid = img.width() if img.width() < max_canvas_size else max_canvas_size
    hei = img.height() if img.height() < max_canvas_size else max_canvas_size
    canvas.configure(width=wid, height=hei, bg='#DDFFDD',
                     scrollregion=(0, 0, img.width(), img.height()))
    canvas.create_image(0, 0, image=img, anchor=tkinter.NW, tag="age")

    root.maxsize(img.width(), img.height())

    def canvas_click(event):
        print("canvas clicked")
        pos = (int(event.widget.canvasx(event.x)),
               int(event.widget.canvasy(event.y)))
        #print("clicked "+str(pos))
        #print("color is "+str(PIL_Img.getpixel(pos)))
        # PIL_Img.putpixel(pos, (255, 0, 0)) #赤く塗りたいときはここに
        global img
        img = PIL.ImageTk.PhotoImage(PIL_Img)
        event.widget.delete("hoge")
        event.widget.create_oval(
            pos[0]-5, pos[1]-5, pos[0]+5, pos[1]+5, tag="hoge")

        root.title = "calculating now..."
        # TODO async化
        result_img = execute(PIL_Img, [pos])

        img = PIL.ImageTk.PhotoImage(result_img)
        event.widget.itemconfigure(tagOrId="age", image=img)
        file_name = "gradation_" + datetime.datetime.now().strftime("%m_%d_%H_%M_%S")
        if devmode:
            result_img.save(os.path.dirname(__file__)+os.sep+file_name)
        else:
            save_path = tkinter.filedialog.asksaveasfilename(
                initialdir=init_dir, initialfile=file_name, filetypes=[("", "*.png")])
            result_img.save(save_path+".png")

    canvas.bind("<Button-1>", canvas_click)
    root.mainloop()
    return 0


if __name__ == "__main__":
    main()
