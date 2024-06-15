package elasticsearch_utils

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/elastic/go-elasticsearch/v8"
	"github.com/elastic/go-elasticsearch/v8/esapi"
)

var Es *elasticsearch.Client

type Doc struct {
	Url  string   `json:"url"`
	Tags []string `json:"tags"`
}

func Connect() {
	elasticsearch_url, exists := os.LookupEnv("ELASTICSEARCH_URL")
	if !exists {
		log.Println("elasticsearch url environment not found")
	}

	cfg := elasticsearch.Config{
		Addresses: []string{elasticsearch_url},
	}
	var err error
	Es, err = elasticsearch.NewClient(cfg)
	if err != nil {
		log.Fatalf("Error create client Elasticsearch: %s", err)
	}
}

func SetElasticsearch() {
	// Создание индекса
	createIndex()

	// Индексация документа
	doc := Doc{
		Url: "https://example.com/video1",
		Tags: []string{
			"dog",
			"cat",
			"магазин",
		},
	}
	indexDocument(doc)
}

func createIndex() {
	mapping := `{
        "mappings": {
            "properties": {
                "url": { "type": "keyword" },
                "tags": { "type": "text" }
            }
        }
    }`

	req := esapi.IndicesCreateRequest{
		Index: "videos",
		Body:  strings.NewReader(mapping),
	}

	res, err := req.Do(context.Background(), Es)
	if err != nil {
		log.Fatalf("Error creating the index: %s", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		log.Fatalf("Error response: %s", res)
	}
	log.Println("Index created successfully")
}

func IndexDocument(doc Doc) {
	data, err := json.Marshal(doc)
	if err != nil {
		log.Fatalf("Error marshaling the document: %s", err)
	}

	req := esapi.IndexRequest{
		Index:   "videos",
		Body:    strings.NewReader(string(data)),
		Refresh: "true",
	}

	res, err := req.Do(context.Background(), Es)
	if err != nil {
		log.Fatalf("Error indexing the document: %s", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		log.Fatalf("Error response: %s", res)
	}
	log.Println("Document indexed successfully")
}

func Search(phrase string) {
	query := map[string]interface{}{
		"query": map[string]interface{}{
			"match": map[string]interface{}{
				"tags": phrase,
			},
		},
	}

	var buf strings.Builder
	if err := json.NewEncoder(&buf).Encode(query); err != nil {
		log.Fatalf("Error encoding query: %s", err)
	}

	req := esapi.SearchRequest{
		Index: []string{"videos"},
		Body:  strings.NewReader(buf.String()),
	}

	res, err := req.Do(context.Background(), Es)
	if err != nil {
		log.Fatalf("Error getting response: %s", err)
	}
	defer res.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(res.Body).Decode(&result); err != nil {
		log.Fatalf("Error parsing the response body: %s", err)
	}

	// Вывод результатов
	fmt.Printf("Results: %+v\n", result)
}

func PrintDocs() {
	// Создаем запрос на поиск всех документов в индексе
	req := esapi.SearchRequest{
		Index: []string{"videos"},
	}

	// Выполняем запрос
	res, err := req.Do(context.Background(), Es)
	if err != nil {
		log.Fatalf("Error searching documents: %s", err)
	}
	defer res.Body.Close()

	// Проверяем успешность запроса
	if res.IsError() {
		log.Fatalf("Error response: %s", res)
	}

	// Декодируем ответ
	var response map[string]interface{}
	if err := json.NewDecoder(res.Body).Decode(&response); err != nil {
		log.Fatalf("Error parsing the response body: %s", err)
	}

	// Обрабатываем ответ, выводим список документов
	hits := response["hits"].(map[string]interface{})["hits"].([]interface{})
	for _, hit := range hits {
		// Получаем _id и остальные поля документа
		doc := hit.(map[string]interface{})
		id := doc["_id"]
		source := doc["_source"]
		log.Printf("Document ID: %v, Document: %v", id, source)
	}
}
