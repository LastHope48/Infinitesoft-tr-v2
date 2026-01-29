FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

EXPOSE 7860
CMD ["python", "app.py"]
