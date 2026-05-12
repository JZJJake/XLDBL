#!/bin/bash
# Start backend
cd backend
python main.py &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

# Wait
wait
