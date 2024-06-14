package main

import (
	"context"
	"encoding/json"
	"log"
	"main_server/elasticsearch_utils"
	"net/http"
	"os"
	"strings"

	"github.com/elastic/go-elasticsearch/v8"
	"github.com/joho/godotenv"
	"github.com/segmentio/kafka-go"
)

type LoadVideoRequest struct {
	VideoLink   string `json:"video_link"`
	Description string `json:"description"`
}

type VideoLinkMessage struct {
	VideoLink string `json:"video_link"`
}

type DescriptionMessage struct {
	Description string `json:"description"`
}

type Result struct {
	Type  string             `json:"type"`
	Marks map[string]float64 `json:"marks"`
}

// init is invoked before main()
func init() {
	// loads values from .env into the system
	if err := godotenv.Load("info.env"); err != nil {
		log.Print("No .env file found")
	}
}

func main() {
	//connect to elasticsearch
	elasticsearch_utils.Connect()

	//elasticsearch_utils.SetElasticsearch()

	http.HandleFunc("/search", getVideosHandler)
	http.HandleFunc("/video/upload", loadVideoHandler)

	//start server
	cur_addr, exists := os.LookupEnv("CUR_ADDR")
	if !exists {
		log.Println("current addres doesn't found")
	}
	log.Println("Starting server on ", cur_addr)
	if err := http.ListenAndServe(cur_addr, nil); err != nil {
		log.Fatalf("Could not start server: %s\n", err.Error())
	}

	//start listen kafka results
	kafkaURL, exists := os.LookupEnv("KAFKA_URL")
	if !exists {
		log.Println("kafka url environment not found")
	}
	brokers := strings.Split(kafkaURL, ",")
	topic_result, exists := os.LookupEnv("TOPIC_RESULT")
	if !exists {
		log.Println("topic result not found")
	}
	go consumeMessages(brokers, topic_result, elasticsearch_utils.Es)

}

func getVideosHandler(w http.ResponseWriter, r *http.Request) {
	phrase := "dog"
	elasticsearch_utils.Search(phrase)

	elasticsearch_utils.PrintDocs()
}

func loadVideoHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		return
	}

	var req LoadVideoRequest
	decoder := json.NewDecoder(r.Body)
	err := decoder.Decode(&req)
	if err != nil {
		http.Error(w, "Error decoding JSON", http.StatusBadRequest)
		return
	}
	if req.VideoLink == "" {
		http.Error(w, "Missing video_link field", http.StatusBadRequest)
		return
	}

	kafkaURL, exists := os.LookupEnv("KAFKA_URL")
	if !exists {
		log.Println("kafka url environment not found")
	}
	brokers := strings.Split(kafkaURL, ",")
	sendToKafka(brokers, req)
}

func sendToKafka(brokers []string, request LoadVideoRequest) {
	topic_video, exists := os.LookupEnv("TOPIC_VIDEO")
	if !exists {
		log.Println("topic for video doesn't found")
	}
	topic_audio, exists := os.LookupEnv("TOPIC_AUDIO")
	if !exists {
		log.Println("topic for audio doesn't found")
	}
	topic_descr, exists := os.LookupEnv("TOPIC_DESCRIPTION")
	if !exists {
		log.Println("description topic doesn't found")
	}

	videoLinkMessage, err := json.Marshal(VideoLinkMessage{VideoLink: request.VideoLink})
	if err != nil {
		log.Fatalf("Failed to marshal video link message: %v\n", err)
	}
	descriptionMessage, err := json.Marshal(DescriptionMessage{Description: request.Description})
	if err != nil {
		log.Fatalf("Failed to marshal description message: %v\n", err)
	}
	produceMessage(brokers, topic_video, videoLinkMessage, []byte(request.VideoLink))
	produceMessage(brokers, topic_audio, videoLinkMessage, []byte(request.VideoLink))
	produceMessage(brokers, topic_descr, descriptionMessage, []byte(request.Description))
}

func produceMessage(brokers []string, topic string, message []byte, key []byte) {
	writer := &kafka.Writer{
		Addr:                   kafka.TCP(brokers...),
		Topic:                  topic,
		AllowAutoTopicCreation: true,
	}
	defer writer.Close()

	err := writer.WriteMessages(context.Background(),
		kafka.Message{
			Key:   key,
			Value: message,
		},
	)
	if err != nil {
		log.Printf("Failed to write message to %s: %v\n", topic, err)
	} else {
		log.Printf("Message sent to %s: %s\n", topic, string(message))
	}
}

func consumeMessages(brokers []string, topic string, esClient *elasticsearch.Client) {
	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: brokers,
		Topic:   topic,
	})
	defer reader.Close()

	ctx := context.Background()

	for {
		for __ := 0; __ < 3; __++ {
			msg, err := reader.ReadMessage(ctx)
			if err != nil {
				if err == context.Canceled {
					break
				}
				log.Printf("Failed to read message: %v\n", err)
				continue
			}

			var result Result
			err = json.Unmarshal(msg.Value, &result)
			if err != nil {
				log.Printf("Error parsing JSON: %v\n", err)
				continue
			}

			processResult(result)
		}
	}
}

func processResult(result Result) {

}
