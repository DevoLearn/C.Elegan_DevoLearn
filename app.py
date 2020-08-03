from flask import Flask, request, render_template, Response, session
import cv2
import numpy as np
import base64
import pandas as pd

app = Flask(__name__)
app.secret_key = 'dljsaklqk24e21cjn!Ew@@dsa5'

@app.route("/", methods = ["GET","POST"])
def home():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file found"
        final_list = {}
        c = 0 #counter variable
        row = 0 #counter for appending rows into dataframe
        df = pd.DataFrame(columns=['name', 'cell', 'X coordinate', 'Y coordinate', 'area'])
        for i in request.files.getlist("file"):
            print(i, end='\n')
            file_name_str = str(i.filename)
            file_name_str = file_name_str.split('.')[0]
            img = i.read() #Read image from FileStorage Object

            img = cv2.imdecode(np.frombuffer(img, np.uint8), -1) #convert to openCV image
            img = cv2.resize(img, (390, 620)) # resize all images to (390, 620)

            img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            img = img[:, :, 2] #extract hue channel
            # blur = cv2.medianBlur(img, 11) # median blurring
            blur = cv2.bilateralFilter(img,9,75,75) # bilateralFilter blurring (seems to have less noise some times)

            # Gradient Morphology
            kernel = np.ones((3,3),np.uint8)
            gradient = cv2.morphologyEx(blur, cv2.MORPH_GRADIENT, kernel) # apply gradient morphology
            op = cv2.morphologyEx(gradient, cv2.MORPH_OPEN, kernel) # apply opening morphology

            ret,thresh1 = cv2.threshold(op,1,255,cv2.THRESH_BINARY) # thresholding (convert to binary)
            conts, hierarchy = cv2.findContours(thresh1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) # extract contours
            filter_c = []
            for i in range(len(conts)):
                area = cv2.contourArea(conts[i]) #filter out small noises
                if area>500:
                    if (hierarchy[0][i][3] != -1): # ignore the contour of the whole cell
                        filter_c.append(conts[i])

            img = np.dstack((img, img, img))
            for j in range(len(filter_c)):
                M = cv2.moments(filter_c[j]) # compute the center of the contour
                area = cv2.contourArea(filter_c[j])
                cX = int(M["m10"] / M["m00"]) # X coordinate
                cY = int(M["m01"] / M["m00"]) # Y coordinate

                df.loc[row] = [file_name_str] + ['cell'+str(j+1)] + [cX] + [cY] + [area] # add them to df dataframe
                row+=1
                cv2.drawContours(img, [filter_c[j]], -1, (0, 255, 0), 4) # draw extracted contours to display result images
                cv2.circle(img, (cX, cY), 4, (255, 255, 255), -1) #draw centroids
            print(df)
            ret, buf = cv2.imencode( '.jpg', img ) # convert openCV image to byte array

            img_string = base64.b64encode(buf)
            img_string = img_string.decode("utf-8") # convet byte array to base64 string

            final_list[str(c)] = img_string
            c+=1
        json_df = df.to_json(orient='split')
        session["json_df"] = json_df
        df = df[0:0]
        return render_template("result.html", final_list = final_list)
    else:
        print("1111")
        return render_template("index.html")

@app.route('/downloadcsv' )
def downloadcsv():
    print("from download")
    json_df = session.get("json_df",None)
    download_df = pd.read_json(json_df, orient='split')
    print(download_df)
    csv = download_df.to_csv(index=False)
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=SPIM_images_analysis.csv"})

if __name__ == "__main__":
    app.run()