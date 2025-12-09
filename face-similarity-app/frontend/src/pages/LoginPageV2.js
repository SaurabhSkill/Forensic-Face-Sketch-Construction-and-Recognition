import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API_BASE_URL } from "../config";
import "./LoginPageV2.css";

export default function LoginPageV2() {
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState("admin");
  const [showOtpScreen, setShowOtpScreen] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [otp, setOtp] = useState("");
  const [userId, setUserId] = useState(null);
  const [otpTimer, setOtpTimer] = useState(180);
  const [otpDev, setOtpDev] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let timer = null;

    if (showOtpScreen && otpTimer > 0) {
      timer = setInterval(() => {
        setOtpTimer((prev) => prev - 1);
      }, 1000);
    }

    return () => clearInterval(timer);
  }, [showOtpScreen, otpTimer]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = String(seconds % 60).padStart(2, "0");
    return mins + ":" + secs;
  };

  const handleAdminLoginStep1 = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const response = await axios.post(
        API_BASE_URL + "/api/auth/admin/login-step1",
        {
          email,
          password,
        }
      );

      setUserId(response.data.user_id);
      setShowOtpScreen(true);
      setOtpTimer(180);
      setMessage(response.data.message);

      if (response.data.otp_dev) {
        setOtpDev(response.data.otp_dev);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Login failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleAdminLoginStep2 = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const response = await axios.post(
        API_BASE_URL + "/api/auth/admin/login-step2",
        {
          user_id: userId,
          otp,
        }
      );

      localStorage.setItem("token", response.data.token);
      localStorage.setItem("user", JSON.stringify(response.data.user));

      navigate("/admin/dashboard");
    } catch (err) {
      setError(err.response?.data?.error || "OTP verification failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleOfficerLogin = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const response = await axios.post(
        API_BASE_URL + "/api/auth/officer/login",
        {
          email,
          password,
        }
      );

      localStorage.setItem("token", response.data.token);
      localStorage.setItem("user", JSON.stringify(response.data.user));

      if (response.data.requires_password_change) {
        navigate("/change-password");
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err.response?.data?.error || "Login failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const response = await axios.post(
        API_BASE_URL + "/api/auth/admin/resend-otp",
        {
          user_id: userId,
        }
      );

      setOtpTimer(180);
      setMessage("OTP resent successfully!");

      if (response.data.otp_dev) {
        setOtpDev(response.data.otp_dev);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to resend OTP.");
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setShowOtpScreen(false);
    setOtp("");
    setOtpTimer(180);
    setError("");
    setMessage("");
    setOtpDev("");
  };

  return (
    <div className="login-page-v2">
      <div className="login-container">
        <h1 className="logo">FaceFind Forensics</h1>

        {!showOtpScreen ? (
          <>
            <div className="tabs">
              <button
                className={activeTab === "admin" ? "active" : ""}
                onClick={() => setActiveTab("admin")}
              >
                Admin Login
              </button>

              <button
                className={activeTab === "officer" ? "active" : ""}
                onClick={() => setActiveTab("officer")}
              >
                Officer Login
              </button>
            </div>

            <form
              className="form"
              onSubmit={
                activeTab === "admin"
                  ? handleAdminLoginStep1
                  : handleOfficerLogin
              }
            >
              {error && <div className="error">{error}</div>}
              {message && <div className="success">{message}</div>}

              <label>Email</label>
              <input
                type="email"
                value={email}
                required
                onChange={(e) => setEmail(e.target.value)}
              />

              <label>Password</label>
              <input
                type="password"
                value={password}
                required
                onChange={(e) => setPassword(e.target.value)}
              />

              <button className="submit" disabled={loading}>
                {loading ? "Please wait..." : "Login"}
              </button>
            </form>
          </>
        ) : (
          <form className="form" onSubmit={handleAdminLoginStep2}>
            <button className="back" type="button" onClick={handleBack}>
              ← Back
            </button>

            <h2>Enter OTP</h2>

            {error && <div className="error">{error}</div>}
            {message && <div className="success">{message}</div>}

            {otpDev && (
              <div className="dev-otp">DEV OTP: {otpDev}</div>
            )}

            <input
              type="text"
              maxLength="6"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              placeholder="Enter 6-digit OTP"
              required
            />

            <div className="timer">
              Time remaining: {formatTime(otpTimer)}
            </div>

            <button className="submit" disabled={loading || otpTimer === 0}>
              {loading ? "Verifying..." : "Verify OTP"}
            </button>

            <button
              className="resend"
              type="button"
              onClick={handleResendOtp}
              disabled={loading || otpTimer > 150}
            >
              Resend OTP
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
