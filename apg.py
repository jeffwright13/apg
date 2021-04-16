"""
Description:
    apg.py:
    Generate audio program of spoken phrases, with optional background
    sound file mixed in.

    User populates a comma-separated text file with plain-text phrases,
    each followed by an inter-phrase duration. Each line of the file is
    comprised of:
      - one phrase to be spoken
      - a comma
      - a silence duration (specified in seconds)
    Obviously, do not include superfluous commas in this file. An exception
    will occur if you do.

    The script generates and saves a single MP3 file. The base name of the MP3
    file is the same as the specified input file. So, for example, if the
    script is given input file "phrases.txt", the output file will be
    "phrases.mp3".

    The "mix" command is used to mix in background sounds. This command takes
    an extra parameter, the path/filename of a sound file to be mixed in with
    the speech file generated from the phrase file. If the sound file is shorter
    in duration than the generated speech file, it will be looped. If it is
    longer, it will be truncated. The resulting background sound (looped or
    not) will be faded in and out to ensure a smooth transition. Currently,
    only .wav files are supported.


Usage:
    apg [options] <phrase_file>
    apg [options] mix <phrase_file> <sound_file>
    apg -V --version
    apg -h --help

Options:
    -a --attenuation LEV    Set attenuation level of background file (non-
                            negative number indicating dB attenuation)
                            ([default: 0]).
    -p --play               Play program after generating.
    -d --debug              Print debug statements to console.
    -V --version            Show version.
    -h --help               Show this screen.

Commands:
    mix                     Mix files

Arguments:
    phrase_file             Name of comma-separated text file containing
                            phrases and silence durations. Do not include
                            commas in this file.
    sound_file              A file to be mixed into the generated program
                            file. Useful for background music/sounds. Must
                            be in .wav format.

Example <phrase_file> format:
    Phrase One;2
    Phrase Two;5
    Phrase Three;0

Author:
    Jeff Wright <jeff.washcloth@gmail.com>
"""
import os
import sys
import math
from tempfile import NamedTemporaryFile
from pathlib import Path
from binaryornot.check import is_binary
from docopt import docopt
from gtts import gTTS
from audioplayer import AudioPlayer
from pydub import AudioSegment
from progressbar import ProgressBar


def num_lines_in_file(filename):
    """
    Takes text filename ; returns the number of lines in a file
    """
    if is_binary(filename):
        raise TypeError("Provided file, ", filename, " is binary. Must be text.")

    numlines = 0
    with open(filename, "r") as fh:
        for row in fh:
            numlines += 1
    return numlines


def mix(segment1, segment2, seg2_atten=0, fadein=3000, fadeout=6000):
    """
    Mixes two pydub AudioSegments, then fades the result in/out.
    Returns mixed AudioSegment.
    """
    duration1 = len(segment1)
    duration2 = len(segment2)

    if duration1 > duration2:
        times = math.ceil(duration1 / duration2)
        segment2_normalized = segment2 * times
        segment2_normalized = segment2_normalized[:duration1]
    else:
        segment2_normalized = segment2[:duration1]

    return (segment1).overlay(
        (segment2_normalized - float(seg2_atten)).fade_in(fadein).fade_out(fadeout)
    )


def gen_speech(phrase_file, debug=False):
    """
    Generates speech from a comma-separated file.
    Returns Audiosegment.
    """
    with open(phrase_file, "r") as f:
        pbar = ProgressBar(maxval=num_lines_in_file(phrase_file)).start()
        combined = AudioSegment.empty()
        lines = f.readlines()
        num_rows = 0

        for line in lines:
            pbar.update(num_rows)
            num_rows += 1

            try:
                phrase, interval = line.split(";")
            except Exception as e:
                print("Error parsing input file as CSV:")
                print(line)
                print(e.args)
                sys.exit()

            if len(phrase) == 0:
                print("Error: gTTS requires non-empty text to process.")
                print("File: ", phrase_file)
                print("Line number: ", num_rows)
                sys.exit()

            print(phrase) if debug else None
            
            Path.mkdir(Path.cwd() / ".cache") if not Path(Path.cwd() / ".cache").exists() else None
            file = Path.cwd() / ".cache" / (phrase + ".mp3")
            if not Path(file).exists():
                speech = gTTS(phrase)
                speech.save(file)
            speech = AudioSegment.from_file(file, format="mp3")
            combined += speech
            silence = AudioSegment.silent(duration=1000 * int(interval))
            combined += silence

    pbar.finish()
    return combined


def main():
    args = docopt(__doc__, version="Audio Program Generator (apg) v1.4.0")
    phrase_file = args["<phrase_file>"]
    sound_file = args["<sound_file>"]
    save_file = Path(phrase_file).stem + ".mp3"
    print(args)
    print(args) if args["--debug"] else None
    if not os.path.exists(phrase_file):
        sys.exit("Phrase file " + phrase_file + " does not exist. Quitting.")
    if args["mix"] and not os.path.exists(sound_file):
        sys.exit("Sound file " + sound_file + " does not exist. Quitting.")

    speech = gen_speech(args["<phrase_file>"], args["--debug"])

    if args["mix"]:
        bkgnd = AudioSegment.from_file(sound_file, format="wav")
        mixed = mix(speech, bkgnd, args["--attenuation"])
        mixed.export(save_file, format="mp3")
    else:
        speech.export(save_file, format="mp3")

    if args["--play"]:
        AudioPlayer(save_file).play(block=True)


if __name__ == "__main__":
    main()
