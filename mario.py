import cs50

def main():
    print("Height: ", end="")
    height = cs50.get_int()
    
    #Make sure a number between 0 and 23 was entered
    while height < 0 or height > 23:
        print("Height: ", end="")
        height = cs50.get_int()
        
    padding = height - 1
    
    while padding >= 0:
        #Print a row of the pyramid
        printRow(padding, height)
        
        #Move to the next row and decrease padding
        print()
        padding -= 1
        
def printRow(padding, height):
    for i in range(0, padding):
        print(" ", end="")
        
    for i in range(padding, height):
        print("#", end="")
    
    #Print the split
    print("  ", end="")
    
    #print the right side of the pyramid
    for i in range(padding, height):
        print("#", end="")
        
        
if __name__ == "__main__":
    main()