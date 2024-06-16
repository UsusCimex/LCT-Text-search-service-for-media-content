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
	"github.com/segmentio/kafka-go"
)

type LoadVideoRequest struct {
	VideoLink   string `json:"video_link"`
	Description string `json:"description"`
}

type VideoLinkMessage struct {
	VideoLink string `json:"video_link"`
}

type Result struct {
	Type      string   `json:"type"`
	VideoLink string   `json:"video_link"`
	Marks     []string `json:"marks"`
}

func main() {
	//connect to elasticsearch
	elasticsearch_utils.Connect()
	log.Print("Connected to elasticsearch")

	elasticsearch_utils.SetElasticsearch()

	http.HandleFunc("/search", getVideosHandler)
	http.HandleFunc("/video/upload", loadVideoHandler)

	//start server
	if err := http.ListenAndServe(":8080", nil); err != nil {
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
	if r.Method != http.MethodPost {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		return
	}

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
	descriptionMessage, err := json.Marshal(request)
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
		resultsMap := make(map[string][]Result)

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

		_, exists := resultsMap[result.VideoLink]
		if !exists {
			var newArr []Result
			resultsMap[result.VideoLink] = append(newArr, result)
		} else {
			resultsMap[result.VideoLink] = append(resultsMap[result.VideoLink], result)
		}

		if len(resultsMap[result.VideoLink]) == 3 {
			processResult(resultsMap[result.VideoLink], esClient)
			delete(resultsMap, result.VideoLink)
		}
	}
}

func processResult(results []Result, esClient *elasticsearch.Client) {
	var doc elasticsearch_utils.Doc
	doc.Url = results[0].VideoLink
	doc.Tags = []string{}
	for i := 0; i < 3; i++ {
		doc.Tags = append(doc.Tags, results[i].Marks...)
	}

	elasticsearch_utils.IndexDocument(doc)
}
