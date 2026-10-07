#include <WiFi.h>
#include <WebServer.h>
#include <Servo.h>
#include <Wire.h>

// Enter your Wi-Fi credentials.
const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

WebServer server(80);
Servo tiltServo;

const int PAN_STEP=2;
const int PAN_DIR=3;
const int PAN_EN=8;
const int TILT_SIGNAL=9;

int tiltAngle=90;
const int TILT_MIN=15;
const int TILT_MAX=165;
bool enabled=true;
int panDir=0;
int panStepDelay=900;
unsigned long lastStep=0;

void stopAll(){panDir=0;}
void executeCommand(String c){
  c.toLowerCase();
  if(c=="estop"){enabled=false;stopAll();return;}
  if(c=="enable"){enabled=true;return;}
  if(c=="stop"){stopAll();return;}
  if(!enabled)return;
  if(c=="left") panDir=-1;
  else if(c=="right") panDir=1;
  else if(c=="up"){panDir=0;tiltAngle=min(TILT_MAX,tiltAngle+2);tiltServo.write(tiltAngle);}
  else if(c=="down"){panDir=0;tiltAngle=max(TILT_MIN,tiltAngle-2);tiltServo.write(tiltAngle);}
  else if(c=="center"){panDir=0;tiltAngle=90;tiltServo.write(tiltAngle);}
}
void commandRoute(){
  if(server.hasArg("c")) executeCommand(server.arg("c"));
  server.send(200,"text/plain","OK");
}
void setup(){
  Serial.begin(115200);
  pinMode(PAN_STEP,OUTPUT);pinMode(PAN_DIR,OUTPUT);pinMode(PAN_EN,OUTPUT);
  digitalWrite(PAN_EN,LOW);
  tiltServo.attach(TILT_SIGNAL);tiltServo.write(tiltAngle);
  WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
  Serial.print("Connecting");
  while(WiFi.status()!=WL_CONNECTED){delay(300);Serial.print(".");}
  Serial.println();Serial.print("NEXUS IP: ");Serial.println(WiFi.localIP());
  server.on("/",[](){server.send(200,"text/plain","NEXUS CAM NANO ONLINE");});
  server.on("/command",commandRoute);
  server.begin();
}
void loop(){
  server.handleClient();
  if(enabled && panDir!=0 && micros()-lastStep>(unsigned long)panStepDelay){
    lastStep=micros();
    digitalWrite(PAN_DIR,panDir>0?HIGH:LOW);
    digitalWrite(PAN_STEP,HIGH);delayMicroseconds(3);digitalWrite(PAN_STEP,LOW);
  }
}
