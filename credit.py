import cs50

def main():
    print("Number: ", end="")
    number = cs50.get_int()
    
    #If a negative number was entered, set it to 0 to invalidate
    if number < 0:
        number = 0
    
    #Get the length of the number
    length = len(str(number))
    
    #If the length of number is correct for a credit card, validate it
    if length == 13 or length == 15 or length == 16:
        validate(number, length)
    else:
        print("INVALID")
        
def validate(number, length):
    #Convert number to string
    sNumber = str(number)
    
    #Step one and two of the validation process
    validateNum = 0
    
    #Phase One - Multiply every other digit by 2 starting with the next to last digit
    for i in range(length - 2, -1, -2):
        tmp = int(sNumber[i]) * 2
        if tmp >= 10:
            validateNum += tmp % 10
            tmp = tmp // 10
            validateNum += tmp
        else:
            validateNum += tmp
            
    #Phase Two - Add each digit that wasnt multiplied by 2 with phase One
    for i in range(length - 1, -1, -2):
        validateNum += int(sNumber[i])
        
    #Final validation - If it is valid, print which company, else, INVALID
    if validateNum % 10 == 0:
        if sNumber[0] == "3" and sNumber[1] == "4" or sNumber[1] == "7":
            print("AMEX")
        elif sNumber[0] == "4":
            print("VISA")
        elif sNumber[0] == "5" and int(sNumber[1]) >= 1 or int(sNumber[i]) <= 5:
            print("MASTERCARD")
    else:
        print("INVALID")
        
if __name__ == "__main__":
    main()