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
	"path/filepath"
	"strings"
	"time"

	"github.com/fogleman/gg"
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

func handleSignature(w http.ResponseWriter, r *http.Request) {
	start := time.Now()

	current, next := "REPORT PENDING", "PENDING"

	// Fetch TZ data
	resp, err := http.Get("https://d2emu.com/tz")
	if err == nil && resp.StatusCode == http.StatusOK {
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		text := strings.ToUpper(string(body))

		// Extract current zone
		if idx := strings.Index(text, "CURRENT TERROR ZONE:"); idx != -1 {
			end := strings.Index(text[idx:], "NEXT TERROR ZONE:")
			if end == -1 {
				end = len(text) - idx
			}
			snippet := strings.TrimSpace(text[idx+len("CURRENT TERROR ZONE:"):idx+end])
			if strings.Contains(snippet, "IMMUN") {
				snippet = strings.Split(snippet, "IMMUN")[0]
			}
			current = strings.TrimSpace(snippet)
		}

		// Extract next zone
		if idx := strings.Index(text, "NEXT TERROR ZONE:"); idx != -1 {
			snippet := strings.TrimSpace(text[idx+len("NEXT TERROR ZONE:"):])
			if strings.Contains(snippet, "IMMUN") {
				snippet = strings.Split(snippet, "IMMUN")[0]
			}
			next = strings.TrimSpace(snippet)
		}
	} else {
		log.Printf("Fetch error: %v", err)
	}

	// 30-minute countdown
	now := time.Now().UTC()
	minutes := now.Minute()
	secsInMinute := now.Second()
	minsToNext := 30 - (minutes % 30)
	secsToNext := minsToNext*60 - secsInMinute
	if secsToNext < 0 {
		secsToNext = 0
	}
	minsLeft := secsToNext / 60
	secsLeft := secsToNext % 60
	countdown := fmt.Sprintf("%d min, %02d sec until", minsLeft, secsLeft)
	if minsLeft == 0 {
		countdown = fmt.Sprintf("%d seconds until", secsLeft)
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

	// Create new image
	img := image.NewRGBA(image.Rect(0, 0, 300, 140))
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

	y := 55
	for _, line := range textwrap.Wrap(fmt.Sprintf("Now: %s", current), 35) {
		drawText(line, 10, y, color.White, face)
		y += 15
	}

	y += 6
	drawText(countdown, 15, y, color.RGBA{255, 215, 0, 255}, timerFace)
	y += 19

	for _, line := range textwrap.Wrap(fmt.Sprintf("Next: %s", next), 35) {
		drawText(line, 10, y, color.White, face)
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
