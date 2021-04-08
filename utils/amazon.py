import time
import secrets
import boto3


class AudioFile:
    def __init__(self, location: str, id: str):
        self.location = location
        self.id = id

    def __repr__(self):
        return "<AudioFile location={0.location} id={0.id}>".format(self)


class AmazonPolly:
    def __init__(self, access_key: str, secret_access_key: str, region_name: str, voice_id: str = "Brian"):
        self.voice_id = voice_id
        self.polly = boto3.client(
            "polly",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_access_key,
            region_name=region_name
        )

    def create_voice(self, text: str):
        """ Generate a Polly voice and return response """
        response = self.polly.synthesize_speech(
            Text=text, OutputFormat="mp3", VoiceId=self.voice_id
        )

        return response

    @property
    def generate_id(self):
        timestamp = int(time.time())
        random_letters = secrets.token_urlsafe(10)
        return f"{random_letters}-{timestamp}"

    def create_audio_file(self, response, location: str = "."):
        """ Create an MP3 file from self.create_voice() response """
        stream = response.get("AudioStream")

        file_id = self.generate_id
        file_location = f"{location}/{file_id}.mp3"

        with open(file_location, "wb") as f:
            data = stream.read()
            f.write(data)

        return AudioFile(file_location, file_id)
