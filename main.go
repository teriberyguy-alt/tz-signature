package main

import (
	"bytes"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/png"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"golang.org/x/image/font"
	"golang.org/x/image/font/opentype"
	"golang.org/x/image/math/fixed"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "10000"
	}
	http.HandleFunc("/signature.png", handleSignature)
	log.Printf("Listening on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func wrapText(text string, maxLen int) []string {
	var lines []string
	words := strings.Fields(text)
	var current string
	for _, word := range words {
		if len(current)+len(word)+1 > maxLen && current != "" {
			lines = append(lines, current)
			current = ""
		}
		if current != "" {
			current += " "
		}
		current += word
	}
	if current != "" {
		lines = append(lines, current)
	}
	return lines
}

func handleSignature(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	current, next := "REPORT PENDING", "PENDING"

	// Fetch TZ data
	resp, err := http.Get("https://d2emu.com/tz")
	if err == nil && resp.StatusCode == http.StatusOK {
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		text := string(body) // Keep case as-is for better matching

		// Split into lines for easier parsing
		lines := strings.Split(text, "\n")
		inCurrent := false
		inNext := false
		var currentZones, nextZones []string

		for _, line := range lines {
			line = strings.TrimSpace(line)
			if line == "" {
				continue
			}

			if strings.HasPrefix(line, "Current Terror Zone:") {
				inCurrent = true
				inNext = false
				// Skip the prefix and date/immunities
				parts := strings.Split(line, ".")
				if len(parts) > 2 {
					zonePart := strings.Join(parts[2:], ".") // After second period
					zones := strings.Fields(strings.TrimSpace(zonePart))
					currentZones = append(currentZones, zones...)
				}
				continue
			}

			if strings.HasPrefix(line, "Next Terror Zone:") {
				inCurrent = false
				inNext = true
				// Similar, but next often has no date/immun
				parts := strings.Split(line, ":")
				if len(parts) > 1 {
					zonePart := strings.TrimSpace(parts[1])
					zones := strings.Fields(zonePart)
					nextZones = append(nextZones, zones...)
				}
				continue
			}

			// Collect zone lines (they are often on separate lines or space-separated)
			if inCurrent && !strings.Contains(line, "immunities") && !strings.HasPrefix(line, "Next") {
				zones := strings.Fields(line)
				if len(zones) > 0 {
					currentZones = append(currentZones, zones...)
				}
			}

			if inNext && !strings.Contains(line, "immunities") {
				zones := strings.Fields(line)
				if len(zones) > 0 {
					nextZones = append(nextZones, zones...)
				}
			}
		}

		// Join zones with " + "
		if len(currentZones) > 0 {
			current = strings.Join(currentZones, " + ")
		}
		if len(nextZones) > 0 {
			next = strings.Join(nextZones, " + ")
		}
	} else {
		log.Printf("Fetch error: %v", err)
	}

	// 30-minute countdown (to next :00 or :30 UTC)
	now := time.Now().UTC()
	minutes := now.Minute()
	secs := now.Second()
	minsToNext := 30 - (minutes % 30)
	if minsToNext == 30 {
		minsToNext = 0
	}
	secsToNext := minsToNext*60 - secs
	if secsToNext < 0 {
		secsToNext += 3600
	}
	minsLeft := secsToNext / 60
	secsLeft := secsToNext % 60
	countdown := fmt.Sprintf("%d min %02d sec until next", minsLeft, secsLeft)
	if minsLeft == 0 && secsLeft > 0 {
		countdown = fmt.Sprintf("%d sec until next", secsLeft)
	} else if secsToNext == 0 {
		countdown = "Rotating now..."
	}

	// Load background
	bgFile, err := os.Open("bg.jpg")
	if err != nil {
		log.Printf("bg.jpg error: %v", err)
		http.Error(w, "Error loading background", http.StatusInternalServerError)
		return
	}
	defer bgFile.Close()
	bgImg, _, err := image.Decode(bgFile)
	if err != nil {
		log.Printf("Decode bg error: %v", err)
		http.Error(w, "Error decoding background", http.StatusInternalServerError)
		return
	}

	// Create new image (height 160 for multi-lines)
	img := image.NewRGBA(image.Rect(0, 0, 300, 160))
	draw.Draw(img, img.Bounds(), bgImg, bgImg.Bounds().Min, draw.Src)

	// Load font
	fontData, err := os.ReadFile("font.ttf")
	if err != nil {
		log.Printf("font.ttf error: %v", err)
		http.Error(w, "Error loading font", http.StatusInternalServerError)
		return
	}
	f, err := opentype.Parse(fontData)
	if err != nil {
		log.Printf("Parse font error: %v", err)
		http.Error(w, "Error parsing font", http.StatusInternalServerError)
		return
	}
	face := opentype.NewFace(f, &opentype.FaceOptions{
		Size:    12,
		DPI:     72,
		Hinting: font.HintingFull,
	})
	timerFace := opentype.NewFace(f, &opentype.FaceOptions{
		Size:    13,
		DPI:     72,
		Hinting: font.HintingFull,
	})

	// Draw text with shadow
	drawText := func(text string, x, y int, col color.Color, fnt font.Face) {
		d := &font.Drawer{
			Dst:  img,
			Src:  image.NewUniform(col),
			Face: fnt,
			Dot:  fixed.P(x, y),
		}
		// Shadow
		d.Dot = fixed.P(x+1, y+1)
		d.Src = image.Black
		d.DrawString(text)
		// Main text
		d.Dot = fixed.P(x, y)
		d.Src = image.NewUniform(col)
		d.DrawString(text)
	}

	// Draw Current Zone
	y := 25
	drawText("Current Zone:", 10, y, color.White, face)
	y += 18
	for _, line := range wrapText(current, 32) {
		drawText(line, 15, y, color.White, face)
		y += 15
	}

	// Draw Countdown
	y += 10
	drawText(countdown, 10, y, color.RGBA{255, 215, 0, 255}, timerFace)

	// Draw Next Zone
	y += 22
	drawText("Next Zone:", 10, y, color.White, face)
	y += 18
	for _, line := range wrapText(next, 32) {
		drawText(line, 15, y, color.White, face)
		y += 15
	}

	// Send PNG
	buf := new(bytes.Buffer)
	if err := png.Encode(buf, img); err != nil {
		log.Printf("PNG encode error: %v", err)
		http.Error(w, "Error encoding image", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "image/png")
	w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
	w.Write(buf.Bytes())
	log.Printf("Sig generated in %v", time.Since(start))
}
