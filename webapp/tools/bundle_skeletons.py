import os, glob, json

SKELETON_GLOB='../static/skeletons/*.*'
SKELETON_OUT='../static/js/skeletons.js'

def get_shortname(filename):
    basename = os.path.basename(filename)
    try:
        i = basename.rindex('.')
    except ValueError:
        return basename
    else:
        return basename[:i]

def main():
    skeletons = {}
    for filename in glob.glob(SKELETON_GLOB):
        shortname = get_shortname(filename)
        with open(filename, 'r') as f:
            skeletons[shortname] = f.read().strip()
    with open(SKELETON_OUT, 'w') as f:
        f.write('var skeletons = ')
        json.dump(skeletons, f)
            
            

if __name__ == '__main__':
    main()

