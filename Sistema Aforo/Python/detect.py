import numpy as np
import cv2
import person
import time

# code version of https://github.com/Gupu25/PeopleCounter
# implemented with live streaming and variable image resolution

try:
    log = open("log.txt", "w")
except:
    print("No se puede abrir el archivo log")


cnt_up = 0
cnt_down = 0

url = "http://192.168.1.67/mjpeg/1"

cap = cv2.VideoCapture(url)

   #############################
   #  GET-STREAMING-PROPERTIES #
   #############################

if cap.isOpened():
    absolute_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    absolute_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = cv2.VideoWriter("output.avi", cv2.VideoWriter_fourcc(*"MJPG"), fps, (int(absolute_w), int(absolute_h))
    )


absoluteFrameArea = absolute_h * absolute_w
absoluteAreaTH = absoluteFrameArea / 250
print("Area Threshold", absoluteAreaTH)

# Lineas de entrada/salida
line_up = int(2 * (absolute_h / 5))
line_down = int(3 * (absolute_h / 5))

up_limit = int(1 * (absolute_h / 5))
down_limit = int(4 * (absolute_h / 5))

print("Red line y:", str(line_down))
print("Blue line y:", str(line_up))


line_down_color = (255, 0, 0)
line_up_color = (0, 0, 255)
pt1 = [0, line_down]
pt2 = [absolute_w, line_down]
pts_L1 = np.array([pt1, pt2], np.int32)
pts_L1 = pts_L1.reshape((-1, 1, 2))
pt3 = [0, line_up]
pt4 = [absolute_w, line_up]
pts_L2 = np.array([pt3, pt4], np.int32)
pts_L2 = pts_L2.reshape((-1, 1, 2))

pt5 = [0, up_limit]
pt6 = [absolute_w, up_limit]
pts_L3 = np.array([pt5, pt6], np.int32)
pts_L3 = pts_L3.reshape((-1, 1, 2))
pt7 = [0, down_limit]
pt8 = [absolute_w, down_limit]
pts_L4 = np.array([pt7, pt8], np.int32)
pts_L4 = pts_L4.reshape((-1, 1, 2))

# Substractor de fondo
fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=True)

# Elementos estructurantes para filtros morfoogicos
kernelOp = np.ones((3, 3), np.uint8)
kernelOp2 = np.ones((5, 5), np.uint8)
kernelCl = np.ones((11, 11), np.uint8)

# Variables
font = cv2.FONT_HERSHEY_SIMPLEX
persons = []
max_p_age = 5
pid = 1

while cap.isOpened():

    ret, frame = cap.read()

    ###Recorder###
   

    for i in persons:
        i.age_one()  
    #########################
    #   PRE-PROCESAMIENTO   #
    #########################

    # Aplica substraccion de fondo
    fgmask = fgbg.apply(frame)
    fgmask2 = fgbg.apply(frame)

    # Binariazcion para eliminar sombras (color gris)
    try:
        ret, imBin = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
        ret, imBin2 = cv2.threshold(fgmask2, 200, 255, cv2.THRESH_BINARY)
        # Opening (erode->dilate) para quitar ruido.
        mask = cv2.morphologyEx(imBin, cv2.MORPH_OPEN, kernelOp)
        mask2 = cv2.morphologyEx(imBin2, cv2.MORPH_OPEN, kernelOp)
        # Closing (dilate -> erode) para juntar regiones blancas.
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernelCl)
        mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernelCl)
    except:
        print("EOF")
        print("UP:", cnt_up)
        print("DOWN:", cnt_down)
        break
    #################
    #   CONTORNOS   #
    #################

    contours0, hierarchy = cv2.findContours(
        mask2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    for cnt in contours0:
        area = cv2.contourArea(cnt)
        if area > absoluteAreaTH:
            #################
            #   TRACKING    #
            #################


            M = cv2.moments(cnt)
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            x, y, w, h = cv2.boundingRect(cnt)

            new = True
            if cy in range(up_limit, down_limit):
                for i in persons:
                    if abs(x - i.getX()) <= w and abs(y - i.getY()) <= h:
                        new = False
                        i.updateCoords(
                            cx, cy
                        )  
                        if i.going_UP(line_down, line_up) == True:
                            cnt_up += 1
                            print(
                                "ID:",
                                i.getId(),
                                "crossed going up at",
                                time.strftime("%c"),
                            )
                            log.write(
                                "ID: "
                                + str(i.getId())
                                + " crossed going up at "
                                + time.strftime("%c")
                                + "\n"
                            )
                        elif i.going_DOWN(line_down, line_up) == True:
                            cnt_down += 1
                            print(
                                "ID:",
                                i.getId(),
                                "crossed going down at",
                                time.strftime("%c"),
                            )
                            log.write(
                                "ID: "
                                + str(i.getId())
                                + " crossed going down at "
                                + time.strftime("%c")
                                + "\n"
                            )
                        break
                    if i.getState() == "1":
                        if i.getDir() == "down" and i.getY() > down_limit:
                            i.setDone()
                        elif i.getDir() == "up" and i.getY() < up_limit:
                            i.setDone()
                    if i.timedOut():
                        
                        index = persons.index(i)
                        persons.pop(index)
                        del i  
                if new == True:
                    p = person.MyPerson(pid, cx, cy, max_p_age)
                    persons.append(p)
                    pid += 1
         
            # Se dibuja en la imagen la caja alrededor de la figura y el centro de la caja
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            img = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
  
    #########################
    # DIBUJAR TRAYECTORIAS  #
    #########################
    for i in persons:

        cv2.putText(
            frame,
            str(i.getId()),
            (i.getX(), i.getY()),
            font,
            0.3,
            i.getRGB(),
            1,
            cv2.LINE_AA,
        )

    ################
    # IMAGE RENDER #
    ################
    str_up = "UP: " + str(cnt_up)
    str_down = "DOWN: " + str(cnt_down)
    frame = cv2.polylines(frame, [pts_L1], False, line_down_color, thickness=2)
    frame = cv2.polylines(frame, [pts_L2], False, line_up_color, thickness=2)
    frame = cv2.polylines(frame, [pts_L3], False, (255, 255, 255), thickness=1)
    frame = cv2.polylines(frame, [pts_L4], False, (255, 255, 255), thickness=1)
    cv2.putText(frame, str_up, (10, 40), font, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, str_up, (10, 40), font, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, str_down, (10, 90), font, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, str_down, (10, 90), font, 0.5, (255, 0, 0), 1, cv2.LINE_AA)

    # Muestra la imagen en vivo, desactivar una vez optimizado el sistema
    # para mayor rendimiento
    cv2.imshow("Frame", frame)

    # Graba el video actual para poder mejorar el sistema
    out.write(frame)
    # cv2.imshow("Mask", mask)

    if cv2.waitKey(1) >= 0:
        cv2.destroyAllWindows()
        exit(0)


#################
#   LIMPIEZA    #
#################
log.flush()
log.close()
cap.release()
out.release()
cv2.destroyAllWindows()
