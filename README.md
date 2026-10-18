Welcome to my lock!

This was my attempt at making a fully 3d-printable lock and I think it went pretty well! IN this guide I go through printing, assembly, and generating the key. 

Key generation: 
This project comes with a python script that can generate a key from a 5 digit key code, using only digits from 1-7, which gives almost 17,000 distinct keys. 
Download the python script and the key blank STL and make sure they are in the same folder and that that folder can be accessed from command prompt. 
In the command prompt, paste "py key_code_generator_v16.py"
choose a key code, a 5 digit with digits only between 1-7, and input this into the program. Make sure to remember this number. 
The key STL will be exported to a folder on your device. 

Printing: 
for orienting the STL files most of the files aren't already rotated to the best printing orientation, so you'll make to do this manually. 
None of the parts are that difficult to print when oriented properly, but some--like the core and the Bible--need some supports. 
I added a good bit of tolerance to the parts, so it should still work on lower end printers. 
choose the 5 key pins that correlate with your key code and print them out, make sure to keep track of which is which

Assembly: 
the main reference for assembly is the design files or the images below. 
  1. slide the plug into Bible. The Bible is symmetric, so which side it goes in doesn't matter.
  2. put the C-clip on the back of the plug to hold it in place and make sure it freely rotates
  3. put the key pins in each hole, the first digit of your number should correlate with the pin in the first slot in the Bible, and so on.
  4. insert one driver pin into each hole, there should now be one driver pin and one key pin in each chamber.
  5. insert a spring into each hole. exact dimensions of the spring don't matter as long as it fits and extends above where the Bible cover will be.
  6. slide the Bible cover into the Bible while pushing down the springs to stop them from getting in the way.
  7. insert the key and Test it out!

<img width="1830" height="981" alt="Screenshot 2026-10-18 163946" src="https://github.com/user-attachments/assets/5f444150-49bd-4389-9bf4-49afd722877a" />
<img width="1480" height="791" alt="Screenshot 2026-10-18 152004" src="https://github.com/user-attachments/assets/01dfe1b0-37a9-484a-b7ab-a841923c5fde" />
<img width="1812" height="875" alt="Screenshot 2026-10-18 150026" src="https://github.com/user-attachments/assets/a92a3fec-9ee9-4995-a262-27a57aa437a2" />
