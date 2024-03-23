from setuptools import setup

setup(
    name = "T U B E F A L L E R",
    version = "1.0.0",
    options = {
        "build_apps" : {
            "include_patterns" : [
                "**/*.png",
                "**/*.jpg",
                "**/*.ogg",
                "**/*.txt",
                "**/*.bam",
                "**/*.mp3",
                "**/*.dat",
                "**/*.cur",
                "**/*.ttf",
                "**/*.vert",
                "**/*.frag",
                "fonts/*",
                "textures/*",
                "music/*",
            ],
            "exclude_patterns" : [
                "ModelViewer/*",
                "build/*",
                "dist/*",
                ".git/*",
                "*__pycache__*",
                "README.md",
                "requirements.txt",
                "setup.py"
            ],
            "gui_apps" : {
                "T U B E F A L L E R" : "main.py"
            },
            "icons" : {
                "T U B E F A L L E R" : [
                    "icon/icon512.png"
                ]
            },
            "plugins" : [
                "pandagl",
                "p3openal_audio",
            ],
            "platforms" : [
                "manylinux2014_x86_64",
                #"macosx_10_6_x86_64",
                "win_amd64"
            ],
            "log_filename" : "$USER_APPDATA/FPSProgram/output.log",
            "log_append" : False
        }
    }
)
