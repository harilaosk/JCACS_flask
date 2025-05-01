# JointCycleACS
*Joint Cycling Automated Control Software*

## This software has been created to control a small joint implant testing rig for an university group design project.

## What this project does
* Provide a GUI for a simple user experience
* Allow the creation of sequences of activities to define testing cycles
* Interface with the rig to be able to perform testing cyles

## Installation
Computer Software with UI: 
* Either Download or clone this repository. 
* Install the required libraries.
* Run app.py
* Open the local server (address outputted on run) in your browser.
Ardunio Code
* Open the arduinoCode.ino file in Ardunio IDE. Flash to your arduino- Mega advised. 
* If you want to debug the arduino-software interface without rig operation, please be sure to alter the debug state in the ino file prior to flashing.

## Use of UI
The UI has been designed to be intuitive to use. Please see below for the 
* Define activities (/activities). Actvities can be edited within the table.
* Add activities to sequence (/activities)
* Add repeat counts (within table), and reorder as appropiate. (/sequence) Where the base activity has been updated, the update can be feed through to the sequence by clicking update on the relevent activity rows.
* Select the port the ardunio is connected to (/run_cycles)
* Run the sequence (/run_cycles)
* Export log (/run_cycles)

* The exporting and importing of activities and sequences as csv files may improve the efficiency of bulk sequence creation. 

## Future Work
Any future work should take in mind user feedback and requested feature improvements.

![image](https://github.com/user-attachments/assets/936b4769-3950-4c67-9d1a-dcb22a505a0a)
![image](https://github.com/user-attachments/assets/b69fa768-c44f-420e-9672-15dfd3f01289)
![image](https://github.com/user-attachments/assets/1d9250a4-aa71-4dc8-9b0f-2cb38f5ea7e4)

