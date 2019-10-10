package disco

import (
	"testing"

	v1 "github.com/sapcc/kubernetes-operators/disco/pkg/apis/disco.stable.sap.cc/v1"
	"github.com/stretchr/testify/assert"
	"k8s.io/api/extensions/v1beta1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func TestKeyFunc(t *testing.T) {
	stim := map[string]interface{}{
		"ingress/default/myIngress": &v1beta1.Ingress{
			TypeMeta: metav1.TypeMeta{
				Kind: "Ingress",
			},
			ObjectMeta: metav1.ObjectMeta{
				Namespace: "default",
				Name:      "myIngress",
			},
		},
		"ingress/default/ingressNoTypeMeta": &v1beta1.Ingress{
			ObjectMeta: metav1.ObjectMeta{
				Namespace: "default",
				Name:      "ingressNoTypeMeta",
			},
		},
		"record/default/myrecord": &v1.DiscoRecord{
			TypeMeta: metav1.TypeMeta{
				Kind: v1.DiscoRecordKind,
			},
			ObjectMeta: metav1.ObjectMeta{
				Namespace: "default",
				Name:      "myrecord",
			},
		},
		"record/default/recordNoTypeMeta": &v1.DiscoRecord{
			ObjectMeta: metav1.ObjectMeta{
				Namespace: "default",
				Name:      "recordNoTypeMeta",
			},
		},
	}

	for expectedKey, obj := range stim {
		key, err := keyFunc(obj)
		assert.NoError(t, err, "there should be no error creating the key")
		assert.Equal(t, expectedKey, key, "the keys should be equal")
	}
}

func TestSplitKeyFunc(t *testing.T) {
	objType, ns, name, err := splitKeyFunc("ingress/default/myingress")
	assert.NoError(t, err, "there should be no error splitting the key")
	assert.Equal(t, "ingress", objType, "the object type should be equal")
	assert.Equal(t, "default", ns, "the namespace should be equal")
	assert.Equal(t, "myingress", name, "the name should be equal")

	_, _, _, err = splitKeyFunc("/foo")
	assert.EqualError(t, err, "unexpected key format: \"/foo\"", "there should be an error splitting an invalid key")
}
