def expandasciiescapes(text: str) -> str:
    i = 0
    while i < len(text):
        if text[i] == '%':
            str1 = text[:i:]
            str2 = "%(char)c" % {'char': int(text[i + 1:i + 3:], 16)}
            str3 = text[i + 3::]  # what if % is later than 3rd to last?
            text = str1 + str2 + str3
        i += 1
    
    return text

print(expandasciiescapes("%"))