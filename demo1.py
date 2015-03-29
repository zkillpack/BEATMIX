import echonest.remix.audio as audio
import numpy as np
import scipy.spatial
import random
from pydub import AudioSegment
from scipy.io.wavfile import write
import glob

from pyechonest import config
config.ECHO_NEST_API_KEY="4AMNMQMNTL9LURSWX"

class Song:
    def __init__(self, song_path):
        self.title = song_path[12:-4]
        print "Opening " + self.title

        self.audio_file = audio.LocalAudioFile(song_path)

        self.out_file = "temp.wav"

        # Get segments in strong meter positions
        self.beat_starts = set([bar.children()[0] for bar in self.audio_file.analysis.bars])
        self.segs = np.concatenate([quantum.segments for quantum in self.beat_starts])
        self.indexed_segs = {seg: i for i, seg in enumerate(self.segs)}

    def render_sorted(self, sort_function):
        """
        Renders the segments of a song sorted by a given function to wav for debugging
        """
        audio.getpieces(self.audio_file, sorted(self.segs, key = sort_function, reverse = False)).encode(self.out_file)

    def render_segs(self, seglist):
        """
        Renders a given list of segments to wav
        """
        audio.getpieces(self.audio_file, seglist).encode(self.out_file)

    def get_sorted(self, sort_function):
        """
        Returns a list of the song's segments sorted by a given function
        """
        return sorted(self.segs, key = sort_function, reverse = False)

    def top_segs_with_pitch(self, num_segs, pitch):
        """
        For a given pitch class, gets the top 2n segments and returns a randomly
        ordered n of them
        """

        sorted_segs = self.get_sorted((lambda seg: seg.pitches[pitch]))
        try:
            return np.random.choice(sorted_segs[0: 2 * num_segs], num_segs)
        except:
            return np.random.choice(sorted_segs[0:num_segs], num_segs)

    def make_song_from_song(self, segs_per_chord):
        """
        Generates a random chord progression
        and chooses random slices from another song to fill in
        then renders to .wav
        """

        # Generate a random chord progression using a
        # hand-rolled first order pitch class Markov chain
        chord_progs = {0:[4,5,7,8], 4: [5], 5:[0, 7], 7:[0,5], 8:[0]}
        for i in range(8):
            if i == 0:
                current_chord = 0
                chords = [0]
            else:
                next_chord = random.choice(chord_progs[current_chord])
                chords.append(next_chord)
                current_chord = next_chord

        output_segs = []

        print "Rendering song with chords: ", chords, "..."

        lengths = []

        for chord in chords:
            new_segs = self.top_segs_with_pitch(segs_per_chord,chord)
            output_segs.extend(new_segs)
            lengths.append(np.sum([segment.duration for segment in new_segs]))

        self.render_segs(output_segs)

        remixed_song = AudioSegment.from_file(self.out_file)

        self.render_bassline(chords, lengths)

        print "Mixing..."

        bassline = AudioSegment.from_file("tmp/bassline.wav")

        output = remixed_song.overlay(bassline, position = 0)

        print "Done!"
        print "Converting to mp3..."
        output.export("output_songs/" + self.title + "_" + str(segs_per_chord) + ".mp3", format = "mp3")
        print "Done!"

    def render_bassline(self, chords, lengths):
        """
        Given a chord progression and lengths of the chords,
        generates a wav bassline to be combined with a remixed song
        """

        print "Generating bassline..."
        tonic = 65.4064 * (2 ** (self.audio_file.analysis.key["value"] / 12.0))

        def sine_note(f, len):
            timepoints = np.linspace(0, len, len * 44100)
            return (np.sin(2*np.pi*f*timepoints) * 3500).astype(np.int16)

        bassline = np.array([], dtype = np.int16)

        for i, chord in enumerate(chords):
            freq_multiplier = 2 ** (chord / 12.0)
            bassline = np.concatenate((bassline, sine_note(tonic * freq_multiplier, lengths[i])))

        write('tmp/bassline.wav', 44100, bassline)
        print "Done."



for song_title in glob.glob("input_songs/*"):
    # For each song, generate a song each for 4 and 8 segments per chord
    song = Song(song_title)
    song.make_song_from_song(4)
    song.make_song_from_song(8)