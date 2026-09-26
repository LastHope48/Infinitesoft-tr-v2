import os
from flask import Blueprint, request, jsonify, abort
import hmac
import hashlib


bp = Blueprint('api', __name__,subdomain="api")

SAVAS_OYUNU_1_ACHIVEMENTS_SECRET_KEY = os.environ[
    "SAVAS_OYUNU_1_ACHIVEMENTS_SECRET_KEY"
]

ACHIEVEMENTS = {
    "win"
}

@bp.route("/achievements/unlock", methods=["POST"], subdomain="api")
def savas_oyunu_1_achivements_get_hmac():
    data = request.get_json()
    achievement_id = data["achievement_id"]
    device_id = data["device_id"]

    if achievement_id not in ACHIEVEMENTS:
        abort(404)

    message = f"{device_id}:{achievement_id}"

    signature = hmac.new(
        SAVAS_OYUNU_1_ACHIVEMENTS_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return jsonify({
        "hmac": signature
    })

@bp.route("/achievements/verify", methods=["POST"], subdomain="api")
def savas_oyunu_1_achivements_verify_hmac():
    data = request.get_json()

    achievement_id = data["achievement_id"]
    device_id = data["device_id"]
    received_hmac = data["hmac"]

    if achievement_id not in ACHIEVEMENTS:
        abort(404)

    message = f"{device_id}:{achievement_id}"

    expected_hmac = hmac.new(
        SAVAS_OYUNU_1_ACHIVEMENTS_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    valid = hmac.compare_digest(
        received_hmac,
        expected_hmac
    )

    return jsonify({
        "valid": valid
    })

@bp.route("/device/sign", methods=["POST"], subdomain="api")
def savas_oyunu_1_device_sign():
    data = request.get_json()

    device_id = data["device_id"]

    signature = hmac.new(
        SAVAS_OYUNU_1_ACHIVEMENTS_SECRET_KEY.encode(),
        device_id.encode(),
        hashlib.sha256
    ).hexdigest()

    return jsonify({
        "hmac": signature
    })

@bp.route("/device/verify", methods=["POST"], subdomain="api")
def savas_oyunu_1_device_verify():
    data = request.get_json()

    device_id = data["device_id"]
    received_hmac = data["hmac"]

    expected_hmac = hmac.new(
        SAVAS_OYUNU_1_ACHIVEMENTS_SECRET_KEY.encode(),
        device_id.encode(),
        hashlib.sha256
    ).hexdigest()

    valid = hmac.compare_digest(
        received_hmac,
        expected_hmac
    )

    return jsonify({
        "valid": valid
    })
