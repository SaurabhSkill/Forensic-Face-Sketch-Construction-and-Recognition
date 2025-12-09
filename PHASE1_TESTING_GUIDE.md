# Phase 1 Testing Guide - Enhanced Sketch Matching

## 🚀 Quick Start

### Step 1: Restart Backend Server
```bash
# Stop current server (Ctrl+C in terminal)
# Then restart:
npm run dev
```

**Wait for:** `[OK] Server ready on http://localhost:5001`

---

## 🧪 Test Cases

### Test 1: Brown Venddy Sketch
**Expected Improvement:** 78.7% → **82-88%**

1. Upload Brown sketch
2. Click "Search Criminals"
3. Check terminal logs for:
   ```
   Image 1 is sketch: True
   Applying forensic-grade preprocessing...
   ```
4. **Expected Result:**
   - Brown Venddy: **82-88%** (High Confidence)
   - Anna Hardy: **< 20%** (Low/No Match)

---

### Test 2: Anna Hardy Sketch
**Expected Improvement:** 49.7% → **65-75%**

1. Upload Anna sketch
2. Click "Search Criminals"
3. **Expected Result:**
   - Anna Hardy: **65-75%** (Medium-High Confidence)
   - Brown Venddy: **< 30%** (Low Match)

---

### Test 3: Jesse Sketch
**Expected Improvement:** Better rejection of false positives

1. Upload Jesse sketch
2. Click "Search Criminals"
3. **Expected Result:**
   - Brown Venddy: **< 35%** (down from 39%)
   - Anna Hardy: **< 10%** (down from 0%)

---

## 📊 What to Look For in Terminal

### Good Signs ✅
```
Image 1 is sketch: True
Applying forensic-grade preprocessing...
Running DeepFace verification with enhanced images...
[OK] Comparison completed in 14.5 seconds
  Distance: 0.18 (threshold: 0.30)
  Similarity: 0.82 (82.0%)
  Verified: True
  Confidence: high
```

### What Changed:
- "forensic-grade preprocessing" message (new)
- "enhanced images" message (new)
- Slightly longer time (+0.5-1s)
- Better similarity scores

---

## ⏱️ Performance Check

**Before:** ~13.5s per criminal
**After:** ~14-14.5s per criminal
**Difference:** +0.5-1 second (acceptable)

---

## 🎯 Success Criteria

### Phase 1 is Successful if:
✅ Brown sketch → Brown: **> 80%**
✅ Anna sketch → Anna: **> 65%**
✅ Wrong matches: **< 35%**
✅ Processing time: **< 16s per criminal**

### If Results Are Good:
- Keep Phase 1
- Consider Phase 2 (ArcFace) for even better accuracy

### If Results Are Not Good:
- Easy rollback: `git reset --hard HEAD~1`
- Restart server
- Back to 78% accuracy

---

## 🐛 Troubleshooting

### Issue: Server won't start
**Solution:** Check for Python errors in terminal

### Issue: No improvement in scores
**Solution:** 
1. Check terminal for "forensic-grade preprocessing" message
2. If missing, code didn't apply
3. Restart server

### Issue: Server is slower
**Solution:** This is expected (+0.5-1s), acceptable for forensic use

### Issue: Errors in terminal
**Solution:**
1. Copy error message
2. Share with Kiro
3. Easy rollback available

---

## 📞 Next Steps

### If Phase 1 Works Well:
1. Test with more sketches
2. Document results
3. Consider Phase 2 for 88-92% accuracy

### If Phase 1 Doesn't Help:
1. Rollback changes
2. Try different approach
3. No harm done!

---

**Remember:** This is Phase 1 - safe, quick, zero risk!
