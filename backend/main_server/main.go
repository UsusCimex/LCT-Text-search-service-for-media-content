package main

import (
	"io"
	"log"
	"net/http"
	"os"

	"github.com/joho/godotenv"
)

// Функция для пересылки запросов
func proxyRequest(w http.ResponseWriter, r *http.Request, targetURL string) {
	req, err := http.NewRequest(r.Method, targetURL, r.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	for key, values := range r.Header {
		for _, value := range values {
			req.Header.Add(key, value)
		}
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(resp.StatusCode)
	w.Header().Set("Content-Type", resp.Header.Get("Content-Type"))
	w.Write(body)
}

func getVideosHandler(w http.ResponseWriter, r *http.Request) {
	get_videos_url, exists := os.LookupEnv("GET_VIDEOS_URL")
	if !exists {
		log.Println("url for get_videos server doesn't found")
	}
	proxyRequest(w, r, get_videos_url)
}

func loadVideoHandler(w http.ResponseWriter, r *http.Request) {
	load_video_url, exists := os.LookupEnv("LOAD_VIDEOS_URL")
	if !exists {
		log.Println("url for load_video server doesn't found")
	}
	proxyRequest(w, r, load_video_url)
}

// init is invoked before main()
func init() {
	// loads values from .env into the system
	if err := godotenv.Load("info.env"); err != nil {
		log.Print("No .env file found")
	}
}

func main() {
	http.HandleFunc("/getVideos", getVideosHandler)
	http.HandleFunc("/loadVideo", loadVideoHandler)

	cur_addr, exists := os.LookupEnv("CUR_ADDR")
	if !exists {
		log.Println("current addres doesn't found")
	}

	log.Println("Starting server on ", cur_addr)
	if err := http.ListenAndServe(cur_addr, nil); err != nil {
		log.Fatalf("Could not start server: %s\n", err.Error())
	}
}
