import requests, zipfile, io, sys, time, os, shutil

def DownloadSave(url, current):
    data = requests.get(url)

    with zipfile.ZipFile(io.BytesIO(data.content)) as f:
        f.extractall()
    
    structure = os.listdir()
    for i in structure:
        if not i in current:
            return i
    return False

def TransferFiles(directory):
    for root, dirs, files in os.walk(directory):
        for i in files:
            d = (root + '\\').split('\\',1)[1]
            if not os.path.isdir('\\' + d):
                os.makedirs(d)
            shutil.move(root + '\\' + i, d+i)
def main():
    current = os.listdir()
    url = sys.argv[-1]
    
    NewDirectory = DownloadSave(url, current)
    if NewDirectory == False:
        print('No new directories...')
        exit()

    TransferFiles(NewDirectory)
    shutil.rmtree(NewDirectory, ignore_errors=True)

if __name__ == '__main__':
    for i in reversed(range(0)):
        print(str(i+1) + '...')
        time.sleep(1)
    print('Downloading...')
    main()