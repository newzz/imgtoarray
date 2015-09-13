# imgtoarray
helper library that converts an image into a hard-coded C/Systemerilog/Intel Hex file with palette reduction option

# What does it do?
This library is be able to do simple conversion of RGB(A) images to hard-coded C/C++/SystemVerilog arrays, and furthermore, hex file. It samples and constructs histograms, groups neighbor colors together in the same bin, then reduce the palette to the N colors with highest frequencies (can be specified, default 16 (4-bit representation)). Each pixel in an image is then "rounded" to one of the N colors, whichever the nearest. The pixels are then encoded with a palette number, a much shorter representation than 32-bit BGRA value. The program outputs a hex file that contains consecutive palettized images (each address (32-bit) holds 32/4-bit = 8 consecutive pixels), and another small hex file which address represents palette number, and its 32-bit value represents the color encoded by that palette number.
